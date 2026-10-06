"""
Car Command Definitions and Entity-to-Action Mapper for BYD DiLink (Branch A).

Defines standard vehicle action constants and translates NLU entities and
utterances into structured car action dictionaries and natural Arabic spoken confirmations.
"""

import re
from typing import Any, Dict, Optional, Tuple

from nlu_classifier import normalize_arabic


# =====================================================================
# Standard Command Constants
# =====================================================================

# Air Conditioning / Climate Control
AC_ON = "AC_ON"
AC_OFF = "AC_OFF"
SET_AC_TEMP = "SET_AC_TEMP"
AC_TEMP_UP = "AC_TEMP_UP"
AC_TEMP_DOWN = "AC_TEMP_DOWN"
FAN_SPEED = "FAN_SPEED"

# Windows & Sunroof
WINDOW_OPEN = "WINDOW_OPEN"
WINDOW_CLOSE = "WINDOW_CLOSE"
WINDOW_FRONT_LEFT = "WINDOW_FRONT_LEFT"
WINDOW_ALL = "WINDOW_ALL"
SUNROOF_OPEN = "SUNROOF_OPEN"
SUNROOF_CLOSE = "SUNROOF_CLOSE"

# Media & Volume
MEDIA_PLAY = "MEDIA_PLAY"
MEDIA_PAUSE = "MEDIA_PAUSE"
MEDIA_NEXT = "MEDIA_NEXT"
MEDIA_PREV = "MEDIA_PREV"
VOLUME_UP = "VOLUME_UP"
VOLUME_DOWN = "VOLUME_DOWN"
VOLUME_SET = "VOLUME_SET"

# Navigation
NAV_TO = "NAV_TO"
OPEN_MAPS = "OPEN_MAPS"

# Apps & System Controls
OPEN_APP = "OPEN_APP"
DILINK_SETTINGS = "DILINK_SETTINGS"
DILINK_ENERGY_APP = "DILINK_ENERGY_APP"
DILINK_CAMERA_360 = "DILINK_CAMERA_360"


# =====================================================================
# Entity-to-Action Mapping Engine
# =====================================================================

def _extract_destination(text: str, norm_text: str) -> Optional[str]:
    """Extracts target navigation destination from text."""
    # Pattern: (وديني|خذني الى|الملاحة الى|روح على) <الوجهة>
    m = re.search(r"(?:وديني|خذني|دلني|الملاحه|الملاحة|نافيجيشن|روح)\s+(?:الى|إلى|الي|علي|على)?\s*(.+)", text, re.IGNORECASE)
    if m:
        dest = m.group(1).strip()
        # Clean trailing punctuation
        dest = re.sub(r"[.,?!؟]+$", "", dest).strip()
        if dest and dest not in ["الخرائط", "الخريطه", "الخريطة"]:
            return dest
    return None


def _extract_app_name(text: str, norm_text: str) -> str:
    """Extracts target app name from text."""
    m = re.search(r"(?:افتح|شغل)?\s*(?:تطبيق|برنامج)?\s*(.+)", text, re.IGNORECASE)
    if m:
        app = m.group(1).strip()
        app = re.sub(r"[.,?!؟]+$", "", app).strip()
        if app:
            return app
    return "التطبيق"


def map_entities_to_car_action(entities: Dict[str, Any], raw_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Translates NLU entities and the raw/resolved user utterance into a
    structured car command dict and a natural Arabic spoken confirmation.

    Returns:
        (car_action_dict, spoken_confirmation_arabic)
    """
    entities = entities or {}
    raw_text = raw_text or ""
    norm_text = normalize_arabic(raw_text)

    target = entities.get("target")
    action = entities.get("action")
    value = entities.get("value")

    # Inferred target if not explicitly passed
    if not target:
        if any(w in norm_text for w in ["سقف", "بانوراما"]):
            target = "sunroof"
        elif any(w in norm_text for w in ["شباك", "نافذه", "جامه", "قزاز", "دريشه"]):
            target = "window"
        elif any(w in norm_text for w in ["مكيف", "تكييف", "حراره", "تبريد", "تدفئه", "مروحه"]):
            target = "ac"
        elif any(w in norm_text for w in ["صوت"]):
            target = "volume"
        elif any(w in norm_text for w in ["اغاني", "موسيقى", "ميديا", "راديو"]):
            target = "media"
        elif any(w in norm_text for w in ["خريطه", "خرائط", "ملاحه", "وديني"]):
            target = "navigation"
        elif any(w in norm_text for w in ["تطبيق", "كاميرا", "طاقه", "اعدادات"]):
            target = "app"

    # -----------------------------------------------------------------
    # 1. AC / Climate Control
    # -----------------------------------------------------------------
    if target == "ac":
        # Fan speed control
        if any(w in norm_text for w in ["مروحه", "المروحه", "دفع الهواء", "سرعه المروحه"]):
            spd = value if value is not None else 3
            return (
                {"command": FAN_SPEED, "parameters": {"value": spd, "speed": spd}},
                f"تم ضبط سرعة مروحة التكييف على {spd}."
            )

        if action == "turn_off":
            return (
                {"command": AC_OFF, "parameters": {}},
                "تم إيقاف تشغيل التكييف."
            )

        if action == "decrease" or any(w in norm_text for w in ["ابرد", "أبرد", "برد", "وطي الحراره", "اخفض الحراره", "سقع"]):
            return (
                {"command": AC_TEMP_DOWN, "parameters": {"step": 1}},
                "تم خفض درجة حرارة التكييف لجعل المقصورة أبرد."
            )

        if action == "increase" or any(w in norm_text for w in ["دفي", "دفئ", "سخن", "حراره اعلى", "ارفع الحراره", "ارفع المكيف"]):
            return (
                {"command": AC_TEMP_UP, "parameters": {"step": 1}},
                "تم رفع درجة حرارة التكييف."
            )

        # Set specific temperature
        if action == "set" or (value is not None and value >= 16 and value <= 32):
            temp = value if value is not None else 22
            return (
                {"command": SET_AC_TEMP, "parameters": {"value": temp, "temperature": temp, "unit": "celsius"}},
                f"تم ضبط درجة حرارة التكييف على {temp} درجة مئوية."
            )

        # Turn on default
        return (
            {"command": AC_ON, "parameters": {}},
            "تم تشغيل التكييف."
        )

    # -----------------------------------------------------------------
    # 2. Windows & Sunroof
    # -----------------------------------------------------------------
    if target == "sunroof":
        if action in ["open", "turn_on"] or any(w in norm_text for w in ["افتح", "فك"]):
            return (
                {"command": SUNROOF_OPEN, "parameters": {}},
                "تم فتح فتحة السقف."
            )
        return (
            {"command": SUNROOF_CLOSE, "parameters": {}},
            "تم إغلاق فتحة السقف."
        )

    if target == "window":
        is_close = action == "close" or any(w in norm_text for w in ["سكر", "قفل", "صك", "ارفع", "اغلق"])

        # Driver window specifically
        if any(w in norm_text for w in ["السائق", "سايق", "يسار", "شباك السائق", "نافذه السائق"]):
            act_str = "close" if is_close else "open"
            return (
                {"command": WINDOW_FRONT_LEFT, "parameters": {"window": "front_left", "action": act_str}},
                f"تم {'إغلاق' if is_close else 'فتح'} نافذة السائق."
            )

        # All windows
        if any(w in norm_text for w in ["كل النوافذ", "كل الشبابيك", "جميع النوافذ", "جميع الشبابيك", "كل الدرايش", "كل القزاز"]):
            act_str = "close" if is_close else "open"
            return (
                {"command": WINDOW_ALL, "parameters": {"window": "all", "action": act_str}},
                f"تم {'إغلاق' if is_close else 'فتح'} جميع النوافذ."
            )

        if is_close:
            return (
                {"command": WINDOW_CLOSE, "parameters": {"window": "all"}},
                "تم إغلاق النوافذ."
            )
        return (
            {"command": WINDOW_OPEN, "parameters": {"window": "all"}},
            "تم فتح النوافذ."
        )

    # -----------------------------------------------------------------
    # 3. Volume & Media
    # -----------------------------------------------------------------
    if target == "volume":
        if action == "turn_off" or any(w in norm_text for w in ["كتم", "ميوت", "صامت", "صامتة"]):
            return (
                {"command": VOLUME_SET, "parameters": {"value": 0, "mute": True}},
                "تم كتم الصوت."
            )
        if action == "set" or (value is not None and action in ["turn_on", "set"]):
            val = value if value is not None else 10
            return (
                {"command": VOLUME_SET, "parameters": {"value": val}},
                f"تم ضبط مستوى الصوت على {val}."
            )
        if action == "increase" or any(w in norm_text for w in ["علي", "اعلي", "ارفع", "زود", "زيد", "كبر"]):
            return (
                {"command": VOLUME_UP, "parameters": {"step": 1}},
                "تم رفع مستوى الصوت."
            )
        return (
            {"command": VOLUME_DOWN, "parameters": {"step": 1}},
            "تم خفض مستوى الصوت."
        )

    if target == "media":
        if any(w in norm_text for w in ["التالي", "بعده", "اللي بعده", "next"]):
            return (
                {"command": MEDIA_NEXT, "parameters": {}},
                "تشغيل المقطع التالي."
            )
        if any(w in norm_text for w in ["السابق", "قبله", "اللي قبله", "prev", "previous"]):
            return (
                {"command": MEDIA_PREV, "parameters": {}},
                "تشغيل المقطع السابق."
            )
        if action in ["turn_off", "pause", "stop"] or any(w in norm_text for w in ["وقف", "ايقاف", "طفي", "اسكت"]):
            return (
                {"command": MEDIA_PAUSE, "parameters": {}},
                "تم إيقاف تشغيل الوسائط مؤقتاً."
            )
        return (
            {"command": MEDIA_PLAY, "parameters": {}},
            "تم تشغيل الوسائط."
        )

    # -----------------------------------------------------------------
    # 4. Navigation
    # -----------------------------------------------------------------
    if target == "navigation":
        dest = _extract_destination(raw_text, norm_text)
        if dest:
            return (
                {"command": NAV_TO, "parameters": {"destination": dest}},
                f"جاري بدء الملاحة إلى {dest}."
            )
        return (
            {"command": OPEN_MAPS, "parameters": {}},
            "تم فتح تطبيق الخرائط والملاحة."
        )

    # -----------------------------------------------------------------
    # 5. Apps & DiLink System Controls
    # -----------------------------------------------------------------
    if target == "app":
        if any(w in norm_text for w in ["كاميرا 360", "كاميرات 360", "كاميرا"]):
            return (
                {"command": DILINK_CAMERA_360, "parameters": {}},
                "تم فتح كاميرا 360 درجة."
            )
        if any(w in norm_text for w in ["طاقه", "الطاقه", "شاشه الطاقه", "شاشة الطاقة", "بطاريه", "البطاريه"]):
            return (
                {"command": DILINK_ENERGY_APP, "parameters": {}},
                "تم فتح شاشة إدارة الطاقة."
            )
        if any(w in norm_text for w in ["اعدادات", "الاعدادات", "الضبط"]):
            return (
                {"command": DILINK_SETTINGS, "parameters": {}},
                "تم فتح إعدادات النظام."
            )
        app_name = _extract_app_name(raw_text, norm_text)
        return (
            {"command": OPEN_APP, "parameters": {"app_name": app_name}},
            f"تم فتح تطبيق {app_name}."
        )

    # -----------------------------------------------------------------
    # Fallback Car Control Action
    # -----------------------------------------------------------------
    return (
        {"command": "CAR_ACTION", "parameters": {}},
        "تم تنفيذ أمر التحكم بالسيارة."
    )
