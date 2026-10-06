import pytest
from nlu_classifier import normalize_arabic, classify_intent


# =====================================================================
# Tests for normalize_arabic
# =====================================================================

def test_normalize_arabic_basic_and_tashkeel():
    raw = "مَرْحَبَاً، شَغِّلْ التَّكْيِيفَ!"
    normalized = normalize_arabic(raw)
    assert "تكييف" in normalized
    assert "شغل" in normalized
    # Tashkeel should be removed
    for harakah in ["َ", "ُ", "ِ", "ْ", "ّ", "ً", "ٌ", "ٍ"]:
        assert harakah not in normalized


def test_normalize_arabic_alef_variants():
    # أ, إ, آ, ٱ should all become ا
    raw = "أحمد إبراهيم آمن ٱمرأة"
    normalized = normalize_arabic(raw)
    assert normalized == "احمد ابراهيم امن امراه"


def test_normalize_arabic_taa_marbuta():
    # ة should become ه
    raw = "سيارة جميلة وسريعة"
    normalized = normalize_arabic(raw)
    assert normalized == "سياره جميله وسريعه"


def test_normalize_arabic_alif_maqsura():
    # ى should become ي
    raw = "على إلى حتى مشى"
    normalized = normalize_arabic(raw)
    assert normalized == "علي الي حتي مشي"


def test_normalize_arabic_punctuation_and_whitespace():
    raw = "  أهلاً! كيف حالك؟؟، ؛ «رائع»...   "
    normalized = normalize_arabic(raw)
    assert "!" not in normalized
    assert "؟" not in normalized
    assert "«" not in normalized
    assert "»" not in normalized
    assert "،" not in normalized
    assert "؛" not in normalized
    assert normalized == "اهلا كيف حالك رائع"


def test_normalize_arabic_indic_digits():
    raw = "درجة الحرارة ٢٢"
    normalized = normalize_arabic(raw)
    assert "22" in normalized
    assert "٢" not in normalized


# =====================================================================
# Tests for classify_intent: Car Control
# =====================================================================

def test_classify_car_control_ac_turn_on_with_value():
    res = classify_intent("شغل التكييف على درجة 22")
    assert res["intent"] == "car_control"
    assert res["entities"].get("target") == "ac"
    assert res["entities"].get("action") == "turn_on"
    assert res["entities"].get("value") == 22
    assert res["entities"].get("raw_text") == "شغل التكييف على درجة 22"
    assert isinstance(res["confidence"], float)
    assert 0.0 <= res["confidence"] <= 1.0


def test_classify_car_control_ac_dialects():
    # "طفي المكيف"
    res1 = classify_intent("طفي المكيف")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "ac"
    assert res1["entities"].get("action") == "turn_off"

    # "برد الجو" (cooling / decrease temperature)
    res2 = classify_intent("برد الجو شوي")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "ac"
    assert res2["entities"].get("action") in ["decrease", "turn_on", "set"]

    # "دفي السيارة" (heating / increase temperature)
    res3 = classify_intent("دفي السيارة")
    assert res3["intent"] == "car_control"
    assert res3["entities"].get("target") == "ac"
    assert res3["entities"].get("action") == "increase"

    # "دفئ السيارة" (spelled with hamza)
    res4 = classify_intent("دفئ السيارة")
    assert res4["intent"] == "car_control"
    assert res4["entities"].get("target") == "ac"
    assert res4["entities"].get("action") == "increase"


def test_classify_car_control_windows_and_dialects():
    # "نزل الجامة" (Gulf dialect for window down)
    res1 = classify_intent("نزل الجامة")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "window"
    assert res1["entities"].get("action") == "open"

    # "سكر الشباك" (close window)
    res2 = classify_intent("سكر الشباك")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "window"
    assert res2["entities"].get("action") == "close"

    # "افتح الدريشة" (Gulf dialect)
    res3 = classify_intent("افتح الدريشة")
    assert res3["intent"] == "car_control"
    assert res3["entities"].get("target") == "window"
    assert res3["entities"].get("action") == "open"

    # "ارفع القزاز" (close window)
    res4 = classify_intent("ارفع القزاز")
    assert res4["intent"] == "car_control"
    assert res4["entities"].get("target") == "window"
    assert res4["entities"].get("action") == "close"


def test_classify_car_control_sunroof():
    res1 = classify_intent("افتح فتحة السقف")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "sunroof"
    assert res1["entities"].get("action") == "open"

    res2 = classify_intent("سكر البانوراما")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "sunroof"
    assert res2["entities"].get("action") == "close"


def test_classify_car_control_lights():
    res1 = classify_intent("شغل النور")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "light"
    assert res1["entities"].get("action") == "turn_on"

    res2 = classify_intent("طفي الليتات")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "light"
    assert res2["entities"].get("action") == "turn_off"


def test_classify_car_control_volume_and_media():
    # Volume control
    res1 = classify_intent("علي الصوت")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "volume"
    assert res1["entities"].get("action") == "increase"

    res2 = classify_intent("وطي الصوت")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "volume"
    assert res2["entities"].get("action") == "decrease"

    res2_b = classify_intent("قصر على الصوت")
    assert res2_b["intent"] == "car_control"
    assert res2_b["entities"].get("target") == "volume"
    assert res2_b["entities"].get("action") == "decrease"

    res3 = classify_intent("كتم الصوت")
    assert res3["intent"] == "car_control"
    assert res3["entities"].get("target") == "volume"
    assert res3["entities"].get("action") in ["turn_off", "decrease", "set"]

    # Media playback
    res4 = classify_intent("شغل الراديو")
    assert res4["intent"] == "car_control"
    assert res4["entities"].get("target") == "media"
    assert res4["entities"].get("action") == "turn_on"

    res5 = classify_intent("وقف الموسيقى")
    assert res5["intent"] == "car_control"
    assert res5["entities"].get("target") == "media"
    assert res5["entities"].get("action") == "turn_off"


def test_classify_car_control_navigation_and_apps():
    res1 = classify_intent("وديني على المطار")
    assert res1["intent"] == "car_control"
    assert res1["entities"].get("target") == "navigation"

    res2 = classify_intent("افتح الخريطة")
    assert res2["intent"] == "car_control"
    assert res2["entities"].get("target") == "navigation"
    assert res2["entities"].get("action") == "open"

    res3 = classify_intent("افتح كاميرا 360")
    assert res3["intent"] == "car_control"
    assert res3["entities"].get("target") == "app"
    assert res3["entities"].get("action") == "open"


# =====================================================================
# Tests for classify_intent: Chitchat
# =====================================================================

def test_classify_chitchat():
    samples = [
        "كيف حالك اليوم؟",
        "مرحبا يا مساعد",
        "صباح الخير",
        "من أنت؟",
        "مين انت؟",
        "شو اخبارك",
        "شكرا جزيلا",
        "قل لي نكتة",
        "أنا طفشان",
        "مع السلامة",
    ]
    for s in samples:
        res = classify_intent(s)
        assert res["intent"] == "chitchat", f"Failed for chitchat query: '{s}', got {res}"
        assert res["confidence"] >= 0.5


# =====================================================================
# Tests for classify_intent: General Knowledge
# =====================================================================

def test_classify_general_knowledge():
    samples = [
        "كم المسافة بين الأرض والقمر؟",
        "ما هو الطقس في الرياض؟",
        "كيف الجو في دبي غدا؟",
        "كم الساعة في طوكيو؟",
        "ما هي عاصمة فرنسا؟",
        "احسب 25 زائد 30",
        "ما هي آخر الأخبار اليوم؟",
        "من هو مخترع الكهرباء؟",
        "ما هو تعريف الذكاء الاصطناعي؟",
    ]
    for s in samples:
        res = classify_intent(s)
        assert res["intent"] == "general_knowledge", f"Failed for GK query: '{s}', got {res}"
        assert res["confidence"] >= 0.5


# =====================================================================
# Tests for Structure & Edge Cases
# =====================================================================

def test_empty_and_whitespace_input():
    res = classify_intent("")
    assert "intent" in res
    assert "confidence" in res
    assert "entities" in res
    assert res["entities"]["raw_text"] == ""

    res_spaces = classify_intent("   ")
    assert "intent" in res_spaces
    assert res_spaces["entities"]["raw_text"] == "   "


def test_disambiguation_temperature_vs_weather():
    # Weather query specifies a city/location -> general_knowledge
    res_gk = classify_intent("ما هي درجة الحرارة في الرياض؟")
    assert res_gk["intent"] == "general_knowledge"
    assert res_gk["entities"].get("location") == "الرياض"

    # Car control specifies a number -> car_control
    res_car = classify_intent("درجة الحرارة 22")
    assert res_car["intent"] == "car_control"
    assert res_car["entities"].get("target") == "ac"
    assert res_car["entities"].get("value") == 22


def test_written_arabic_numbers():
    res = classify_intent("اضبط التكييف على خمسة وعشرين")
    assert res["intent"] == "car_control"
    assert res["entities"].get("target") == "ac"
    assert res["entities"].get("value") == 25
