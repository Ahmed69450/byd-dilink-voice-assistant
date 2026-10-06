#!/usr/bin/env python3
"""
Kaggle Arabic Chitchat Dataset Fetcher & Formatter for BYD DiLink Assistant.

Downloads conversational datasets from Kaggle or processes local raw files (CSV, TSV, JSON, Parquet),
cleans and deduplicates Arabic question-answer pairs, and formats or merges them into chitchat.json.
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add python source directory for Arabic normalization
APP_PYTHON_DIR = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "main" / "python"
if str(APP_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(APP_PYTHON_DIR))

try:
    from nlu_classifier import normalize_arabic
except ImportError:
    def normalize_arabic(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()


# Common question / prompt column names across open datasets
COMMON_QUESTION_COLS = [
    "question", "query", "prompt", "input", "user", "q", "سؤال", "س", "text", "instruction", "source"
]

# Common answer / response column names
COMMON_ANSWER_COLS = [
    "answer", "response", "reply", "output", "completion", "a", "جواب", "ج", "target"
]


def clean_text(text: str) -> str:
    """
    Cleans text:
    1. Removes HTML tags.
    2. Removes URL links.
    3. Strips control characters.
    4. Collapses redundant spaces.
    """
    if not text:
        return ""
    text = str(text)
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Strip URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Remove control characters except standard whitespace
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_column_name(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    """Finds best matching column name case-insensitively."""
    fields_lower = {f.lower().strip(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in fields_lower:
            return fields_lower[c.lower()]
    return None


def parse_dataset_file(
    filepath: str,
    question_col: Optional[str] = None,
    answer_col: Optional[str] = None,
    min_length: int = 2,
    max_items: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Parses a raw dataset file (CSV, TSV, JSON, JSONL, Parquet) into structured chitchat items:
    [
        {
            "pattern": str,
            "aliases": [],
            "responses": [str, ...]
        }
    ]
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    ext = path.suffix.lower()
    raw_pairs: List[Tuple[str, str]] = []
    grouped: Dict[str, Dict[str, Any]] = {}

    if ext in [".csv", ".tsv", ".txt"]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # Detect dialect / delimiter
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if (ext == ".tsv" or "\t" in sample and "," not in sample) else ","
            try:
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = reader.fieldnames or []
            except Exception:
                fieldnames = []

            q_col = question_col or find_column_name(fieldnames, COMMON_QUESTION_COLS)
            a_col = answer_col or find_column_name(fieldnames, COMMON_ANSWER_COLS)

            if not q_col or not a_col:
                # Fallback to column index 0 and 1 if DictReader fields couldn't match
                f.seek(0)
                csv_reader = csv.reader(f, delimiter=delimiter)
                header = next(csv_reader, None)
                for row in csv_reader:
                    if len(row) >= 2:
                        raw_pairs.append((row[0], row[1]))
            else:
                for row in reader:
                    q = row.get(q_col, "")
                    a = row.get(a_col, "")
                    if q and a:
                        raw_pairs.append((q, a))

    elif ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # If already formatted with pattern and responses, preserve & merge aliases
                        if "pattern" in item and "responses" in item:
                            cleaned_pat = clean_text(item["pattern"])
                            cleaned_resp = [clean_text(r) for r in item.get("responses", []) if clean_text(r)]
                            cleaned_aliases = [clean_text(al) for al in item.get("aliases", []) if clean_text(al)]
                            if len(cleaned_pat) >= min_length and cleaned_resp:
                                norm_p = normalize_arabic(cleaned_pat)
                                if norm_p:
                                    if norm_p not in grouped:
                                        grouped[norm_p] = {
                                            "pattern": cleaned_pat,
                                            "aliases": [],
                                            "responses": []
                                        }
                                    curr_aliases = set(grouped[norm_p]["aliases"])
                                    for al in cleaned_aliases:
                                        if al and al not in curr_aliases and al != grouped[norm_p]["pattern"]:
                                            grouped[norm_p]["aliases"].append(al)
                                            curr_aliases.add(al)
                                    curr_resp = set(grouped[norm_p]["responses"])
                                    for r in cleaned_resp:
                                        if r and r not in curr_resp and len(r) >= min_length:
                                            grouped[norm_p]["responses"].append(r)
                                            curr_resp.add(r)
                                    if max_items and len(grouped) >= max_items:
                                        break
                        else:
                            q_col = question_col or find_column_name(list(item.keys()), COMMON_QUESTION_COLS)
                            a_col = answer_col or find_column_name(list(item.keys()), COMMON_ANSWER_COLS)
                            if q_col and a_col:
                                raw_pairs.append((str(item.get(q_col, "")), str(item.get(a_col, ""))))

    elif ext == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    q_col = question_col or find_column_name(list(item.keys()), COMMON_QUESTION_COLS)
                    a_col = answer_col or find_column_name(list(item.keys()), COMMON_ANSWER_COLS)
                    if q_col and a_col:
                        raw_pairs.append((str(item.get(q_col, "")), str(item.get(a_col, ""))))
                except json.JSONDecodeError:
                    continue

    elif ext == ".parquet":
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            q_col = question_col or find_column_name(list(df.columns), COMMON_QUESTION_COLS)
            a_col = answer_col or find_column_name(list(df.columns), COMMON_ANSWER_COLS)
            if not q_col or not a_col:
                raise ValueError("Could not auto-detect question and answer columns in Parquet file.")
            for _, row in df.iterrows():
                raw_pairs.append((str(row[q_col]), str(row[a_col])))
        except ImportError:
            raise ImportError("pandas or pyarrow is required to read Parquet files. Install them via pip.")
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    # Clean and group by question pattern from raw pairs
    for raw_q, raw_a in raw_pairs:
        cleaned_q = clean_text(raw_q)
        cleaned_a = clean_text(raw_a)

        if len(cleaned_q) < min_length or len(cleaned_a) < min_length:
            continue

        norm_q = normalize_arabic(cleaned_q)
        if not norm_q:
            continue

        if norm_q not in grouped:
            grouped[norm_q] = {
                "pattern": cleaned_q,
                "aliases": [],
                "responses": [cleaned_a]
            }
        else:
            if cleaned_a not in grouped[norm_q]["responses"]:
                grouped[norm_q]["responses"].append(cleaned_a)

        if max_items and len(grouped) >= max_items:
            break

    return list(grouped.values())


def merge_datasets(base_file: str, new_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges new chitchat dialogue items into an existing dataset file."""
    base_path = Path(base_file)
    existing_items: List[Dict[str, Any]] = []

    if base_path.is_file():
        try:
            with open(base_path, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read base file {base_file}: {e}. Starting fresh.")
            existing_items = []

    index: Dict[str, Dict[str, Any]] = {}
    for item in existing_items:
        norm_p = normalize_arabic(item.get("pattern", ""))
        if norm_p:
            index[norm_p] = item

    for item in new_items:
        norm_p = normalize_arabic(item.get("pattern", ""))
        if not norm_p:
            continue

        if norm_p in index:
            target = index[norm_p]
            # Merge aliases
            curr_aliases = set(target.get("aliases", []))
            for alias in item.get("aliases", []):
                if alias and alias not in curr_aliases and alias != target.get("pattern"):
                    target.setdefault("aliases", []).append(alias)
                    curr_aliases.add(alias)

            # Merge responses
            curr_responses = set(target.get("responses", []))
            for resp in item.get("responses", []):
                if resp and resp not in curr_responses:
                    target.setdefault("responses", []).append(resp)
                    curr_responses.add(resp)
        else:
            existing_items.append(item)
            index[norm_p] = item

    return existing_items


def download_kaggle_dataset(dataset_slug: str, target_dir: Optional[str] = None) -> Path:
    """Downloads and unzips a Kaggle dataset using the Kaggle CLI."""
    dest = Path(target_dir) if target_dir else Path("./kaggle_downloads") / dataset_slug.replace("/", "_")
    dest.mkdir(parents=True, exist_ok=True)

    cmd = ["kaggle", "datasets", "download", "-d", dataset_slug, "-p", str(dest), "--unzip"]
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise RuntimeError(
            "Kaggle CLI not found. Please install via 'pip install kaggle' and set ~/.kaggle/kaggle.json credentials."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Kaggle download failed with exit code {e.returncode}: {e}")

    return dest


def main():
    parser = argparse.ArgumentParser(
        description="Download and format Arabic conversational datasets from Kaggle for BYD DiLink Assistant."
    )
    parser.add_argument("-d", "--dataset", help="Kaggle dataset slug (e.g. 'arbml/arabic-chatbot-dataset')")
    parser.add_argument("-i", "--input", help="Path to local raw dataset file (CSV, TSV, JSON, JSONL, Parquet)")
    parser.add_argument(
        "-o",
        "--output",
        default="android/app/src/main/assets/chitchat.json",
        help="Output JSON file path (default: android/app/src/main/assets/chitchat.json)"
    )
    parser.add_argument(
        "-m",
        "--merge",
        action="store_true",
        help="Merge into existing output file instead of replacing"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly overwrite existing output file if it exists"
    )
    parser.add_argument("--question-col", help="Explicit column name for user question")
    parser.add_argument("--answer-col", help="Explicit column name for assistant response")
    parser.add_argument("--min-length", type=int, default=2, help="Minimum character length for utterances")
    parser.add_argument("--max-items", type=int, default=None, help="Maximum number of dialogue patterns to import")

    args = parser.parse_args()

    input_file = args.input

    # Step 1: Download from Kaggle if requested
    if args.dataset:
        print(f"Fetching dataset from Kaggle: {args.dataset}...")
        download_dir = download_kaggle_dataset(args.dataset)
        # Find first suitable data file in download_dir recursively
        supported_exts = {".csv", ".tsv", ".json", ".jsonl", ".parquet"}
        found_files = [f for f in download_dir.rglob("*.*") if f.suffix.lower() in supported_exts and f.is_file()]
        if not found_files:
            print(f"Error: No CSV, TSV, JSON, JSONL, or Parquet files found in downloaded Kaggle directory {download_dir}")
            sys.exit(1)
        input_file = str(found_files[0])
        print(f"Found dataset file: {input_file}")

    if not input_file:
        parser.print_help()
        print("\nError: Please provide either --dataset or --input.")
        sys.exit(1)

    # Step 2: Parse raw dataset
    print(f"Parsing raw dataset from {input_file}...")
    new_items = parse_dataset_file(
        filepath=input_file,
        question_col=args.question_col,
        answer_col=args.answer_col,
        min_length=args.min_length,
        max_items=args.max_items
    )
    print(f"Extracted {len(new_items)} distinct dialogue patterns.")

    # Step 3: Merge or Save
    out_path = Path(args.output)
    if out_path.is_file() and not args.merge and not args.overwrite:
        print(
            f"Error: Output file '{out_path}' already exists.\n"
            "To merge new data with the existing dataset, specify --merge (-m).\n"
            "To overwrite the existing file, specify --overwrite."
        )
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.merge and out_path.is_file():
        print(f"Merging into existing dataset at {out_path}...")
        final_items = merge_datasets(str(out_path), new_items)
    else:
        final_items = new_items

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_items, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(final_items)} dialogue patterns to {out_path}!")


if __name__ == "__main__":
    main()
