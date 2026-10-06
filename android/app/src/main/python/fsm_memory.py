"""
FSM Context Memory & Coreference Resolver for BYD DiLink Voice Assistant.

Maintains multi-turn conversational state, entity retention (locations, car devices,
numeric values), and resolves pronouns and situational references across turns.

Designed for Chaquopy on Android: pure Python standard library, thread-safe.
"""

import re
import time
import threading
from typing import Dict, Any, Optional, List

try:
    from nlu_classifier import normalize_arabic, CAR_TARGETS, _extract_location_entity
except ImportError:
    try:
        from android.app.src.main.python.nlu_classifier import (
            normalize_arabic,
            CAR_TARGETS,
            _extract_location_entity,
        )
    except ImportError:
        def normalize_arabic(text: str) -> str:
            if not text:
                return ""
            # Simple fallback normalizer if nlu_classifier is not in path
            text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
            chars = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"}
            text = "".join(chars.get(c, c) for c in text)
            text = re.sub(r"[؟،؛٪«»!?,.:;\"'`~@#$%^&*()_+=/\\\[\]{}|<>ـ\n\r\t-]", " ", text)
            return re.sub(r"\s+", " ", text).strip()

        CAR_TARGETS = {
            "window": ["شباك", "نافذه", "جامه", "قزاز", "زجاج"],
            "sunroof": ["سقف", "بانوراما", "فتحه السقف"],
            "ac": ["مكيف", "تكييف", "كوندشن", "تبريد", "حراره"],
            "light": ["نور", "انوار", "اضاءه", "ليت", "كشاف"],
            "media": ["موسيقى", "راديو", "ميديا", "اغاني"],
            "volume": ["صوت", "مسجل"],
            "navigation": ["خريطه", "ملاحه", "جي بي اس"],
            "app": ["تطبيق", "شاشه"],
        }

        def _extract_location_entity(norm_text: str) -> Optional[str]:
            m = re.search(r"\bفي\s+([^\s?]+(?:\s+[^\s?]+)?)", norm_text)
            if m:
                loc = m.group(1).strip()
                if _is_non_geo_location(loc):
                    return None
                return loc
            return None


# Positional car terms and non-geographic terms that should not be extracted as locations
CAR_POSITIONAL_TERMS = {
    "الخلف", "الامام", "الامامي", "الخلفي", "المقعد الخلفي", "المقعد الامامي",
    "المقعد", "المقاعد", "السياره", "السيارة", "المركبه", "المركبة",
    "الوسط", "قدام", "ورا", "وراء",
    "يمين", "اليمين", "يسار", "اليسار", "السائق", "الراكب",
    "الشنطه", "الشنطة", "الدرج",
}

NON_GEO_LOCATIONS = {
    "السياره", "السيارة", "البيت", "طريق", "العالم", "هناك", "هنالك", "نفس المكان",
} | CAR_POSITIONAL_TERMS

NON_GEO_LOCATIONS_NORM = {normalize_arabic(t) for t in NON_GEO_LOCATIONS}


def _is_non_geo_location(term: str) -> bool:
    """Checks whether a term is non-geographic or a vehicle positional area."""
    if not term:
        return True
    norm = normalize_arabic(term)
    if norm in NON_GEO_LOCATIONS_NORM:
        return True
    for pos in ["الخلف", "الامام", "المقعد", "السياره", "المركبه"]:
        if pos in norm:
            return True
    return False


# Car action verbs for intent verification & adjustment continuity
CAR_ACTION_VERBS = {
    "شغل", "تشغيل", "ولع", "توليع", "فعل", "تفعيل", "بدا",
    "طفي", "اطفي", "اطفئ", "اطفاء", "طف", "بند", "وقف", "اوقف", "ايقاف", "توقيف", "كتم",
    "افتح", "فتح", "فك", "سكر", "صك", "قفل", "اغلق", "غلق",
    "علي", "اعلي", "رفع", "ارفع", "زود", "زيد", "كبر", "سرع", "دفي", "دفئ", "سخن",
    "وطي", "قصر", "خفض", "اخفض", "نقص", "قلل", "هدي", "رخي", "نزل", "هبط", "برد",
    "اضبط", "ضبط", "حط", "خلي", "اجعل", "سوا", "عيير",
}

# Courtesy prefix pattern supported across car command regexes
COURTESY_PREFIX_PATTERN = r"(?:لو سمحت|لو سمحتي|من فضلك|من فضلكي|بالله|ياريت|يا ريت|تكفى|تكفي|لاهنت|لا هنت)"
CP = rf"(?:({COURTESY_PREFIX_PATTERN})[,،]?\s+)?"


# Canonical Arabic device nouns used when referencing a car target
DEFAULT_TARGET_NOUNS = {
    "ac": "التكييف",
    "window": "النافذة",
    "sunroof": "فتحة السقف",
    "volume": "الصوت",
    "media": "الموسيقى",
    "light": "الاضاءة",
    "navigation": "الخريطة",
    "app": "التطبيق",
}

# Mapping of detected words in user speech to exact preferred forms
DEVICE_KEYWORD_FORMS = {
    "مكيف": "المكيف",
    "المكيف": "المكيف",
    "تكييف": "التكييف",
    "التكييف": "التكييف",
    "شباك": "الشباك",
    "الشباك": "الشباك",
    "نافذه": "النافذة",
    "نافذة": "النافذة",
    "النافذه": "النافذة",
    "النافذة": "النافذة",
    "جامه": "الجامة",
    "الجامه": "الجامة",
    "قزاز": "القزاز",
    "القزاز": "القزاز",
    "سقف": "فتحة السقف",
    "فتحه السقف": "فتحة السقف",
    "فتحة السقف": "فتحة السقف",
    "بانوراما": "البانوراما",
    "البانوراما": "البانوراما",
    "صوت": "الصوت",
    "الصوت": "الصوت",
    "موسيقى": "الموسيقى",
    "الموسيقى": "الموسيقى",
    "راديو": "الراديو",
    "الراديو": "الراديو",
    "اضاءه": "الاضاءة",
    "اضاءة": "الاضاءة",
    "الاضاءه": "الاضاءة",
    "الاضاءة": "الاضاءة",
    "انوار": "الانوار",
    "الانوار": "الانوار",
    "نور": "النور",
    "النور": "النور",
    "خريطه": "الخريطة",
    "الخريطة": "الخريطة",
    "شاشه": "الشاشة",
    "الشاشة": "الشاشة",
    "تطبيق": "التطبيق",
    "التطبيق": "التطبيق",
}

WEATHER_TIME_KEYWORDS = {
    "طقس", "الطقس", "جو", "الجو", "حراره", "الحراره", "حرارة", "الحرارة",
    "ساعه", "الساعه", "ساعة", "الساعة", "وقت", "الوقت", "مطر", "المطر",
    "امطار", "الامطار", "أمطار", "الأمطار",
}


class FSMMemory:
    """
    Finite State Machine Context Memory and Coreference Resolver.
    
    Tracks conversation turns, keeps active topic entities (location, vehicle target,
    temperature/volume values), and resolves anaphoric/pronoun references into
    fully qualified utterances.
    """

    def __init__(self, session_timeout_seconds: float = 300.0) -> None:
        self.session_timeout_seconds: float = float(session_timeout_seconds)
        self._lock = threading.RLock()
        self.state: str = "idle"
        self.last_intent: Optional[str] = None
        self.entities: Dict[str, Any] = {}
        self.last_user_text: Optional[str] = None
        self.last_response_data: Optional[Dict[str, Any]] = None
        self.last_timestamp: Optional[float] = None
        self.turn_count: int = 0
        self.history: List[Dict[str, Any]] = []

    def is_expired(self) -> bool:
        """Checks if the conversational session has expired based on timeout."""
        with self._lock:
            if self.last_timestamp is None:
                return False
            return (time.time() - self.last_timestamp) > self.session_timeout_seconds

    def reset(self) -> None:
        """Clears memory session and resets state machine to IDLE."""
        with self._lock:
            self._clear_state()

    def _clear_state(self) -> None:
        self.state = "idle"
        self.last_intent = None
        self.entities = {}
        self.last_user_text = None
        self.last_response_data = None
        self.last_timestamp = None
        self.turn_count = 0
        self.history = []

    def get_last_topic(self) -> Dict[str, Any]:
        """Returns the last tracked state, intent, and entities."""
        with self._lock:
            if self.is_expired():
                return {
                    "state": "idle",
                    "intent": None,
                    "entities": {},
                    "turn_count": 0,
                    "last_user_text": None,
                    "timestamp": None,
                }
            return {
                "state": self.state,
                "intent": self.last_intent,
                "entities": dict(self.entities),
                "turn_count": self.turn_count,
                "last_user_text": self.last_user_text,
                "timestamp": self.last_timestamp,
            }

    def get_context_entity(self, key: str, default: Any = None) -> Any:
        """Quick accessor for stored context entities like location, target, value."""
        with self._lock:
            if self.is_expired():
                return default
            if key == "state":
                return self.state
            if key == "intent":
                return self.last_intent
            return self.entities.get(key, default)

    def update(
        self,
        user_text: str,
        intent_data: Optional[Dict[str, Any]],
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Updates the active state, last intent, entities (location, vehicle target,
        action, value), timestamp, and history.
        """
        with self._lock:
            if self.is_expired():
                self._clear_state()

            self.last_timestamp = time.time()
            self.turn_count += 1
            self.last_user_text = user_text or ""
            self.last_response_data = response_data

            intent_data = intent_data or {}
            intent = intent_data.get("intent")
            new_entities = intent_data.get("entities") or {}

            # Update state and intent
            if intent:
                self.last_intent = intent
                self.state = intent
            elif self.state == "idle":
                self.state = "active"

            # Merge entities intelligently
            for k, v in new_entities.items():
                if v is not None:
                    if k == "location" and _is_non_geo_location(str(v)):
                        continue
                    self.entities[k] = v

            # If location wasn't in entities but is present in user text, extract it
            # Only extract location if NOT a car command and state is not car_control
            norm_input = normalize_arabic(user_text or "")
            if (
                "location" not in new_entities
                and not self._is_car_command(user_text, norm_input)
                and intent != "car_control"
                and self.state != "car_control"
            ):
                loc_match = re.search(r"\bفي\s+([^\s?؟]+(?:\s+[^\s?؟]+)?)", user_text or "")
                if loc_match:
                    candidate = loc_match.group(1).strip()
                    if not _is_non_geo_location(candidate):
                        self.entities["location"] = candidate
                else:
                    detected_loc = _extract_location_entity(norm_input)
                    if detected_loc and not _is_non_geo_location(detected_loc):
                        self.entities["location"] = detected_loc

            # Detect vehicle target & specific device name mentioned in user speech
            target = self.entities.get("target")
            if not target and self.state == "car_control":
                target = self._detect_target(norm_input)
                if target:
                    self.entities["target"] = target

            if target or self.state == "car_control":
                detected_device_name = self._detect_device_name(norm_input, target)
                if detected_device_name:
                    self.entities["device_name"] = detected_device_name
                elif target and "device_name" not in self.entities:
                    self.entities["device_name"] = DEFAULT_TARGET_NOUNS.get(target, "الجهاز")

            # Record turn in history
            turn_record = {
                "turn": self.turn_count,
                "user_text": user_text,
                "intent": self.last_intent,
                "entities": dict(self.entities),
                "timestamp": self.last_timestamp,
            }
            self.history.append(turn_record)

    def _detect_target(self, norm_text: str) -> Optional[str]:
        """Infers the target device if not provided in intent entities."""
        # sunroof before window
        for kw in CAR_TARGETS.get("sunroof", []):
            norm_kw = normalize_arabic(kw)
            if norm_kw in norm_text:
                return "sunroof"
        order = ["volume", "navigation", "app", "light", "media", "window", "ac"]
        for target in order:
            for kw in CAR_TARGETS.get(target, []):
                norm_kw = normalize_arabic(kw)
                if re.search(rf"(?:^|\s){re.escape(norm_kw)}(?:\s|$)", norm_text):
                    return target
        return None

    def _detect_device_name(self, norm_text: str, target: Optional[str]) -> Optional[str]:
        """Detects the exact device noun used by the speaker."""
        for kw, canonical in DEVICE_KEYWORD_FORMS.items():
            norm_kw = normalize_arabic(kw)
            if re.search(rf"(?:^|\s){re.escape(norm_kw)}(?:\s|$)", norm_text):
                return canonical
        if target:
            return DEFAULT_TARGET_NOUNS.get(target)
        return None

    def _has_explicit_location(self, norm_text: str) -> bool:
        """Checks if the user utterance already contains an explicit location."""
        loc = _extract_location_entity(norm_text)
        return loc is not None

    def _has_explicit_car_target(self, norm_text: str) -> bool:
        """Checks if the user utterance already mentions a car device target or vehicle noun."""
        for target, kws in CAR_TARGETS.items():
            for kw in kws:
                norm_kw = normalize_arabic(kw)
                if re.search(rf"(?:^|\s){re.escape(norm_kw)}(?:\s|$)", norm_text):
                    return True
        if any(w in norm_text.split() for w in ["السياره", "سياره", "مركبه", "المركبه"]):
            return True
        return False

    def _is_car_command(self, user_text: str, norm_text: Optional[str] = None) -> bool:
        """
        Detects whether an utterance is a car control command, car adjustment,
        or vehicle-specific query to avoid cross-domain bleeding.
        """
        if not user_text:
            return False
        if norm_text is None:
            norm_text = normalize_arabic(user_text)

        # 1. Explicit car target or vehicle noun in utterance
        if self._has_explicit_car_target(norm_text):
            return True

        # 2. Car control pronoun / adjustment regex patterns (e.g. "زود فيه", "قصر فيه", "وطي له")
        if re.search(
            r"\b(وطي|قصر|علي|عل|زود|زيد|نقص|اخفض|خفض|ارفع)\s+(له|لها|فيه|فيها|عليه|عليها)\b",
            norm_text,
        ):
            return True

        # Attached pronouns: "سكرها", "طفه", "شغله", "قصره", "ارفعها", "نزله", etc.
        if re.search(
            r"\b(سكر|صك|قفل|اغلق|غلق|افتح|فك|طفي|اطفي|طف|اطف|بند|شغل|ولع|نزل|ارفع|هبط|وطي|قصر|اخفض|خفض|علي|عل|زود|زد|كبر)(ها|ه|يه|يها)\b",
            norm_text,
        ):
            return True

        # "خليه أبرد", "حطها على 22", "اجعله بارد"
        if re.search(r"\b(خليه|خليها|اجعله|اجعلها|حطه|حطها)\b", norm_text):
            return True

        # "نفسه" / "نفسها" with action verbs
        if re.search(r"\b(طفي|اطفي|شغل|سكر|قفل|افتح|فك)\s+(نفسه|نفسها)\b", norm_text):
            return True

        # Comparative AC adjectives: "أبرد", "ابرد", "أسخن", "اسخن", "أدفى", "ادفى", "أحر", "احر"
        if re.search(r"\b(ابرد|أبرد|اسخن|أسخن|ادفى|أدفى|احر|أحر)\b", norm_text):
            return True

        # 3. If car target or car_control state is active in context:
        target = self.entities.get("target")
        if target or self.state == "car_control":
            words = set(norm_text.split())
            if any(act_verb in words for act_verb in CAR_ACTION_VERBS):
                return True

        return False

    def resolve_references(self, user_text: str) -> str:
        """
        Resolves locative references ('هناك', 'فيها', 'نفس المكان') and car device
        pronouns/commands ('خليه أبرد', 'سكرها', 'عليه شوية', 'طفه', 'له', 'نفسه')
        using conversational state memory.
        """
        if not user_text:
            return ""

        with self._lock:
            # If expired or no prior context, return original text unchanged
            if self.is_expired() or self.turn_count == 0:
                return user_text

            norm_text = normalize_arabic(user_text)
            resolved = user_text

            # -------------------------------------------------------------
            # 1. Locative / Knowledge Coreference Resolution
            # -------------------------------------------------------------
            loc = self.entities.get("location")
            is_car = self._is_car_command(user_text, norm_text)

            if loc and not self._has_explicit_location(norm_text):
                # 1a. "هناك" / "هنالك"
                # "في هناك" -> "في <loc>", "من هناك" -> "من <loc>", "الى هناك" -> "الى <loc>", "هناك" -> "في <loc>"
                def replace_honak(m):
                    prefix = m.group(1) or ""
                    waw = m.group(2) or ""
                    prep = m.group(3)
                    if prep:
                        return f"{prefix}{waw}{prep} {loc}"
                    if waw:
                        return f"{prefix}{waw}في {loc}"
                    return f"{prefix}في {loc}"

                resolved = re.sub(
                    r"(^|\s)(و)?(?:(في|من|الى|إلى)\s+)?(هناك|هنالك)(?=\s|[؟?!.,]|$)",
                    replace_honak,
                    resolved,
                )

                # 1b. "فيها" / "فيه" (when location is active)
                # Prevent cross-intent entity bleeding: do NOT replace if it's a car command (e.g. "زود فيه", "قصر فيه")
                if not is_car:
                    def replace_fiha(m):
                        prefix = m.group(1) or ""
                        waw = m.group(2) or ""
                        if waw:
                            return f"{prefix}وفي {loc}"
                        return f"{prefix}في {loc}"

                    resolved = re.sub(
                        r"(^|\s)(و)?(فيها|فيه)(?=\s|[؟?!.,]|$)",
                        replace_fiha,
                        resolved,
                    )

                # 1c. "نفس المكان" / "بنفس المكان" / "في نفس المكان"
                def replace_nafs_makan(m):
                    prefix = m.group(1) or ""
                    prep = m.group(2)
                    if prep in ["ب", "في", "في "]:
                        return f"{prefix}في {loc}"
                    return f"{prefix}{loc}"

                resolved = re.sub(
                    r"(^|\s)(ب|في\s+)?نفس المكان(?=\s|[؟?!.,]|$)",
                    replace_nafs_makan,
                    resolved,
                )

                # 1d. "عندهم" / "عنده"
                resolved = re.sub(
                    r"(^|\s)(و)?(عندهم|عنده)(?=\s|[؟?!.,]|$)",
                    lambda m: f"{m.group(1) or ''}{'و' if m.group(2) else ''}في {loc}",
                    resolved,
                )

                # 1e. Implicit location continuity:
                # e.g., user asks "وكيف الطقس؟" or "كم الساعة؟" with no location mentioned
                # If resolved text still has no location injected and contains weather/time keywords:
                # Verify utterance is NOT a car command (e.g. "كم حرارة التكييف")
                if (
                    not is_car
                    and loc not in resolved
                    and any(kw in norm_text.split() for kw in WEATHER_TIME_KEYWORDS)
                ):
                    punc = ""
                    clean = resolved.strip()
                    if clean.endswith("؟") or clean.endswith("?") or clean.endswith("."):
                        punc = clean[-1]
                        clean = clean[:-1].rstrip()
                    resolved = f"{clean} في {loc}{punc}"

            # -------------------------------------------------------------
            # 2. Car Control Coreference Resolution
            # -------------------------------------------------------------
            target = self.entities.get("target")
            device_name = self.entities.get("device_name") or (
                DEFAULT_TARGET_NOUNS.get(target, "الجهاز") if target else None
            )

            if target and device_name and not self._has_explicit_car_target(norm_text):
                # 2a. "خليه أبرد" / "خليه ابرد" / "خليه على 22" / "خليه عالي" (with optional courtesy prefix)
                m_khaleeh = re.match(
                    rf"^\s*{CP}(خليه|خليها|اجعله|اجعلها|حطه|حطها)\s+(.*)$",
                    resolved,
                )
                if m_khaleeh:
                    courtesy = f"{m_khaleeh.group(1)} " if m_khaleeh.group(1) else ""
                    rest = m_khaleeh.group(3).strip()
                    resolved = f"{courtesy}خلي {device_name} {rest}"

                # 2b. Comparative adjective only for AC: "أبرد", "ابرد", "أسخن", "اسخن", "ادفى"
                elif target == "ac" and re.match(
                    rf"^\s*{CP}(أبرد|ابرد|أسخن|اسخن|أدفى|ادفى|أحر|احر|بارد|حار)(\s+.*)?$",
                    resolved,
                ):
                    m = re.match(
                        rf"^\s*{CP}(أبرد|ابرد|أسخن|اسخن|أدفى|ادفى|أحر|احر|بارد|حار)(\s+.*)?$",
                        resolved,
                    )
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    adj = m.group(2)
                    rest = (m.group(3) or "").strip()
                    suffix = f" {rest}" if rest else ""
                    resolved = f"{courtesy}خلي {device_name} {adj}{suffix}".strip()

                # 2c. Attached object pronoun verbs:
                # "سكرها" / "سكره" (close)
                elif re.match(rf"^\s*{CP}(سكر|صك|قفل|اغلق|غلق)(ها|ه)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(سكر|صك|قفل|اغلق|غلق)(ها|ه)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = m.group(2)
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "افتحها" / "افتحه" / "فكها" / "فكه" (open)
                elif re.match(rf"^\s*{CP}(افتح|فك)(ها|ه)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(افتح|فك)(ها|ه)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = m.group(2)
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "طفه" / "طفيه" / "طفها" / "طفيها" / "بنده" / "بندها" (turn off)
                elif re.match(rf"^\s*{CP}(طفي|اطفي|طف|اطف|بند)(ها|ه|يه|يها)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(طفي|اطفي|طف|اطف|بند)(ها|ه|يه|يها)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = "بند" if m.group(2) == "بند" else "طفي"
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "شغلها" / "شغله" / "ولعها" / "ولعه" (turn on)
                elif re.match(rf"^\s*{CP}(شغل|ولع)(ها|ه)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(شغل|ولع)(ها|ه)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = m.group(2)
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "نزلها" / "نزله" / "ارفعها" / "ارفعه" (raise/lower)
                elif re.match(rf"^\s*{CP}(نزل|ارفع|هبط)(ها|ه)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(نزل|ارفع|هبط)(ها|ه)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = m.group(2)
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "وطيه" / "وطيها" / "قصره" / "قصرها" (decrease)
                elif re.match(rf"^\s*{CP}(وطي|قصر|اخفض|خفض)(ها|ه|يه|يها)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(وطي|قصر|اخفض|خفض)(ها|ه|يه|يها)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    stem = m.group(2)
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # "عليه شوية" / "عليه" (increase volume or raise setting)
                elif re.match(rf"^\s*{CP}(علي|عل|ارف|ارفع|زود|زد|كبر)(ها|ه)(\s+.*)?$", resolved):
                    m = re.match(rf"^\s*{CP}(علي|عل|ارف|ارفع|زود|زد|كبر)(ها|ه)(\s+.*)?$", resolved)
                    courtesy = f"{m.group(1)} " if m.group(1) else ""
                    raw_stem = m.group(2)
                    stem = "علي" if raw_stem in ["علي", "عل"] else raw_stem
                    rest = m.group(4) or ""
                    resolved = f"{courtesy}{stem} {device_name}{rest}".strip()

                # 2d. Preposition + pronoun expressions: "قصر عليه", "ارفع عليه"
                elif re.search(r"\b(قصر|وطي|اخفض|ارفع|علي|زيد|زود)\s+عل(يه|يها)(\s+.*)?$", resolved):
                    m = re.search(r"\b(قصر|وطي|اخفض|ارفع|علي|زيد|زود)\s+عل(يه|يها)(\s+.*)?$", resolved)
                    stem = m.group(1)
                    rest = m.group(3) or ""
                    resolved = re.sub(
                        r"\b(قصر|وطي|اخفض|ارفع|علي|زيد|زود)\s+عل(يه|يها)(\s+.*)?$",
                        f"{stem} على {device_name}{rest}".strip(),
                        resolved,
                    )

                # 2e. "له" / "لها" / "فيه" / "فيها" following action verbs
                # e.g., "وطي له", "علي له", "قصر له", "زود فيه"
                elif re.search(r"\b(وطي|قصر|علي|زود|زيد|نقص|اخفض)\s+(له|لها|فيه|فيها)(\s+.*)?$", resolved):
                    m = re.search(r"\b(وطي|قصر|علي|زود|زيد|نقص|اخفض)\s+(له|لها|فيه|فيها)(\s+.*)?$", resolved)
                    stem = m.group(1)
                    prep_word = m.group(2)
                    rest = m.group(3) or ""
                    replacement = (
                        f"{stem} في {device_name}{rest}".strip()
                        if "في" in prep_word
                        else f"{stem} {device_name}{rest}".strip()
                    )
                    resolved = re.sub(
                        r"\b(وطي|قصر|علي|زود|زيد|نقص|اخفض)\s+(له|لها|فيه|فيها)(\s+.*)?$",
                        replacement,
                        resolved,
                    )

                # 2f. "نفسه" / "نفسها"
                # e.g., "طفي نفسه", "شغل نفسه", "سكر نفسها"
                elif re.search(r"\b(طفي|اطفي|شغل|سكر|قفل|افتح|فك)\s+(نفسه|نفسها)(\s+.*)?$", resolved):
                    m = re.search(r"\b(طفي|اطفي|شغل|سكر|قفل|افتح|فك)\s+(نفسه|نفسها)(\s+.*)?$", resolved)
                    stem = m.group(1)
                    rest = m.group(3) or ""
                    resolved = re.sub(
                        r"\b(طفي|اطفي|شغل|سكر|قفل|افتح|فك)\s+(نفسه|نفسها)(\s+.*)?$",
                        f"{stem} {device_name}{rest}".strip(),
                        resolved,
                    )

            return resolved
