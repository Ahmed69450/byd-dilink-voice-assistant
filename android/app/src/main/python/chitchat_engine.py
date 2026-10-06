"""
Arabic Chitchat Engine for BYD DiLink Voice Assistant (Branch C).

Provides:
- ChitchatEngine: Offline conversational engine with fuzzy string matching.
- levenshtein_distance: Pure-Python Levenshtein edit distance calculation.
- levenshtein_similarity: Normalized similarity ratio [0.0, 1.0].
"""

import difflib
import json
import os
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from nlu_classifier import normalize_arabic


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes the Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    if len(s1) > len(s2):
        s1, s2 = s2, s1

    previous_row = list(range(len(s1) + 1))
    for i, c2 in enumerate(s2):
        current_row = [i + 1] + [0] * len(s1)
        for j, c1 in enumerate(s1):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row[j + 1] = min(insertions, deletions, substitutions)
        previous_row = current_row

    return previous_row[-1]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Computes normalized Levenshtein similarity in [0.0, 1.0]."""
    if s1 == s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return max(0.0, 1.0 - (dist / max_len))


SHORT_PARTICLES = {
    "شو", "لا", "ما", "هل", "كم", "مين", "لو", "كي", "لن", "لم",
    "عن", "من", "في", "او", "ثم", "بل", "قد"
}


DEFAULT_FALLBACK_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern": "من أنت",
        "aliases": ["مين انت", "عرفني بنفسك", "ما هو اسمك", "شو اسمك"],
        "responses": [
            "أنا المساعد الصوتي الذكي لسيارة بي واي دي (BYD DiLink). كيف يمكنني مساعدتك اليوم؟",
            "أنا رفيقك الصوتي في رحلتك على متن سيارة BYD DiLink."
        ]
    },
    {
        "pattern": "صباح الخير",
        "aliases": ["صباح النور", "يسعد صباحك", "صباح الورد"],
        "responses": [
            "صباح النور والسرور! أتمنى لك يوماً رائعاً وقيادة ممتعة.",
            "صباح الورد والياسمين! كيف يمكنني مساعدتك في هذا الصباح؟"
        ]
    },
    {
        "pattern": "شكرا",
        "aliases": ["شكراً", "مشكور", "تسلم", "يعطيك العافيه"],
        "responses": [
            "العفو! في خدمتك دائماً.",
            "الله يعافيك ويسلمك، على الرحب والسعة!"
        ]
    }
]


class ChitchatEngine:
    """
    Offline Arabic chitchat engine using fuzzy string matching.
    Zero heavy dependencies; runs entirely on pure Python standard library.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self.patterns: List[Dict[str, Any]] = []
        self._indexed_patterns: List[Dict[str, Any]] = []
        self._load_data(data_path)
        self._index_patterns()

    def _load_data(self, data_path: Optional[str] = None) -> None:
        """Loads chitchat dataset from specified path or standard candidate paths."""
        target_path: Optional[Path] = None

        if data_path:
            p = Path(data_path)
            if not p.is_file():
                raise FileNotFoundError(f"Chitchat dataset not found at: {data_path}")
            target_path = p
        else:
            candidates = [
                # Bundled inside python directory alongside chitchat_engine.py (Chaquopy unpack target)
                Path(__file__).resolve().parent / "chitchat.json",
                # Android assets relative to chitchat_engine.py
                Path(__file__).resolve().parent.parent / "assets" / "chitchat.json",
                # Project root relative
                Path.cwd() / "android" / "app" / "src" / "main" / "assets" / "chitchat.json",
                Path.cwd() / "assets" / "chitchat.json",
                Path.cwd() / "chitchat.json",
            ]
            for cand in candidates:
                if cand.is_file():
                    target_path = cand
                    break

        if target_path and target_path.is_file():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    self.patterns = json.load(f)
            except Exception as e:
                # Fallback to default in-memory patterns if file is corrupt
                self.patterns = list(DEFAULT_FALLBACK_PATTERNS)
        else:
            self.patterns = list(DEFAULT_FALLBACK_PATTERNS)

    def _index_patterns(self) -> None:
        """Pre-normalizes all patterns and aliases for fast sub-50ms matching."""
        self._indexed_patterns = []
        for item in self.patterns:
            pattern = item.get("pattern", "")
            aliases = item.get("aliases", [])
            responses = item.get("responses", [])

            variants: List[str] = []
            if pattern:
                variants.append(normalize_arabic(pattern))

            for alias in aliases:
                norm_alias = normalize_arabic(alias)
                if norm_alias and norm_alias not in variants:
                    variants.append(norm_alias)

            self._indexed_patterns.append({
                "item": item,
                "variants": variants,
                "variant_word_sets": [set(v.split()) for v in variants],
            })

    def size(self) -> int:
        """Returns the total number of dialogue patterns loaded."""
        return len(self.patterns)

    def _score_candidate(self, norm_query: str, query_words: set, cand: str, cand_words: set) -> float:
        """Calculates fuzzy similarity between normalized query and candidate variant."""
        if not norm_query or not cand:
            return 0.0

        if norm_query == cand:
            return 1.0

        # Short queries or single grammatical particles cannot fuzzy-match non-identical candidates
        if len(norm_query) <= 2 or norm_query in SHORT_PARTICLES:
            return 0.0

        # Candidate single short particle cannot fuzzy match non-identical queries
        if len(cand) <= 2 or cand in SHORT_PARTICLES:
            return 0.0

        # If both are single words, enforce strict typo tolerance (only distance <= 1 for words >= 4 chars)
        if len(query_words) == 1 and len(cand_words) == 1:
            if min(len(norm_query), len(cand)) <= 3:
                return 0.0
            dist = levenshtein_distance(norm_query, cand)
            if dist <= 1:
                return max(0.0, 1.0 - (dist / max(len(norm_query), len(cand))))
            return 0.0

        score = 0.0

        # Word-boundary phrase containment checks (replaces raw substring checks)
        # 1. Candidate phrase appears with word boundaries in query
        cand_in_query = bool(re.search(rf'(?:^|\s){re.escape(cand)}(?:\s|$)', norm_query))
        if cand_in_query:
            if len(cand_words) >= 2:
                sub_score = 0.50 + 0.50 * (len(cand) / len(norm_query))
            else:
                # No arbitrary +0.50 floor for single short words
                sub_score = len(cand) / len(norm_query)
            score = max(score, sub_score)

        # 2. Query phrase appears with word boundaries in candidate
        query_in_cand = bool(re.search(rf'(?:^|\s){re.escape(norm_query)}(?:\s|$)', cand))
        if query_in_cand:
            if len(query_words) >= 2:
                sub_score = 0.50 + 0.50 * (len(norm_query) / len(cand))
            else:
                # No arbitrary +0.50 floor for single short words
                sub_score = len(norm_query) / len(cand)
            score = max(score, sub_score)

        # 3. Word subset overlap
        if cand_words and cand_words.issubset(query_words):
            if len(cand_words) >= 2:
                word_score = 0.55 + 0.45 * (len(cand_words) / len(query_words))
            else:
                word_score = len(cand_words) / len(query_words)
            score = max(score, word_score)

        # 4. Multi-word fuzzy matching using significant matching blocks (min block size 3)
        sm = difflib.SequenceMatcher(None, norm_query, cand)
        sig_blocks = [b.size for b in sm.get_matching_blocks() if b.size >= 3]
        cand_cov = sum(sig_blocks) / len(cand) if cand else 0.0

        if cand_cov >= 0.70:
            seq_sim = sm.ratio()
            score = max(score, seq_sim)

        lev_sim = levenshtein_similarity(norm_query, cand)
        if lev_sim >= 0.75:
            score = max(score, lev_sim)

        return min(1.0, score)

    def get_best_match(self, query: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Finds the highest scoring pattern for the query.
        Returns: (matching_item_dict, confidence_score)
        """
        if not query or not query.strip():
            return None, 0.0

        norm_query = normalize_arabic(query)
        if not norm_query:
            return None, 0.0

        query_words = set(norm_query.split())
        best_item: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for entry in self._indexed_patterns:
            item_score = 0.0
            variants = entry["variants"]
            word_sets = entry["variant_word_sets"]

            for cand, cand_words in zip(variants, word_sets):
                s = self._score_candidate(norm_query, query_words, cand, cand_words)
                if s > item_score:
                    item_score = s
                if item_score >= 1.0:
                    break

            if item_score > best_score:
                best_score = item_score
                best_item = entry["item"]
                if best_score >= 1.0:
                    break

        return best_item, round(best_score, 4)

    def get_response(
        self,
        query: str,
        threshold: float = 0.55,
        fallback: Optional[str] = None
    ) -> Optional[str]:
        """
        Matches user query against chitchat patterns.
        If similarity >= threshold, returns a random friendly response.
        Otherwise returns fallback (or None).
        """
        best_item, score = self.get_best_match(query)
        if best_item and score >= threshold:
            responses = best_item.get("responses", [])
            if responses:
                return random.choice(responses)

        return fallback
