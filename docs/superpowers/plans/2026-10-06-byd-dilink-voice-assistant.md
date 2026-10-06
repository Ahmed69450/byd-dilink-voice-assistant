# خطة تنفيذ المساعد الصوتي لسيارات BYD DiLink (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** بناء نظام مساعد صوتي غير معتمد على النماذج التوليدية الضخمة (No Heavy LLMs) لسيارات BYD DiLink (نظام Android)، يدعم التحكم بالسيارة بدون إنترنت، واسترجاع المعرفة العامة عبر الـ APIs، والسوالف التفاعلية بالعربية، مع التجهيز كـ Android APK ورفع المشروع إلى مستودع GitHub.

**Architecture:** بنية هجينة تعتمد على تطبيق Android مكتوب بـ Kotlin يتولى واجهة Push-to-Talk والتحكم بأنظمة السيارة (CarControlBridge) وتوليد الصوت (TTS)، ومحرك معالجة لغوية بـ Python مدمج داخل التطبيق عبر Chaquopy يحتوي على مصنف النوايا (TF-IDF + Rules)، وذاكرة السياق (FSM Memory)، ومطابقة السوالف (Fuzzy Matching على chitchat.json)، وعملاء الـ APIs (Wolfram, DuckDuckGo, Open-Meteo, NewsAPI, World Time API).

**Tech Stack:** Kotlin, Android SDK (API 28+), Chaquopy (Python 3.8+), Vosk STT, Piper/Android TTS, Requests, Fuzzy Matching (Levenshtein), JSON, Gradle.

**Spec:** `docs/superpowers/specs/2026-10-06-byd-dilink-voice-assistant-design.md`

## Global Constraints
- نظام التشغيل المستهدف: Android 9+ (API 28+) المتوافق مع أنظمة شاشات BYD DiLink.
- عدم استخدام نماذج لغوية توليدية ضخمة (NO Heavy LLMs) لتوفير الأداء والسرعة محلياً.
- دعم اللغة العربية الفصحى وأهم مرادفات اللهجات المستخدمة في أوامر القيادة والسوالف.
- العمل دون اتصال بالإنترنت في المسار A (أوامر السيارة) والمسار C (السوالف) مع رد مهذب عند غياب الشبكة في المسار B.

## Review Focus
1. مدخل نصي بدون اتصال بالإنترنت يطلب الطقس أو المعرفة: يجب أن يرد برسالة صوتية واضحة تشرح عدم توفر الشبكة دون انهيار التطبيق.
2. جملة تحكم في السيارة تحتوي على مرادفات لهجات (مثل "برد الجو" أو "نزل الجامة"): يجب أن يصنفها فوراً كـ `car_control` مع استخراج العملية المناسبة.
3. سؤال متعدد الأدوار باستخدام الضمائر (مثال: "كم الساعة في طوكيو؟" ثم "ما هو الطقس هناك؟"): يجب أن تحل وحدة الذاكرة "هناك" كـ "طوكيو".
4. سؤال chitchat مع خطأ إملائي بسيط: يجب أن تعثر خوارزمية Fuzzy Matching على الإجابة المناسبة وتجيب بسلاسة.
5. استدعاء أمر تحكم في السيارة أثناء تشغيل الموسيقى: يجب أن يتم خفض الصوت وتنفيذ الأمر ثم تأكيده صوتياً.

---

### Task 1: معالج النصوص العربي ومصنف النوايا (NLU Classifier & Normalizer)

**Files:**
- Create: `android/app/src/main/python/nlu_classifier.py`
- Test: `tests/test_nlu_classifier.py`

**Interfaces:**
- Produces:
  - `normalize_arabic(text: str) -> str`
  - `classify_intent(text: str) -> dict` returning `{"intent": "car_control"|"chitchat"|"general_knowledge", "confidence": float, "entities": dict}`

- [ ] **Step 1: كتابة الاختبار الفاشل (Write the failing test)**
```python
# tests/test_nlu_classifier.py
import pytest
from nlu_classifier import normalize_arabic, classify_intent

def test_normalize_arabic():
    raw = "مَرْحَبَاً، شَغِّلْ التَّكْيِيفَ!"
    normalized = normalize_arabic(raw)
    assert "تكييف" in normalized
    assert "َ" not in normalized

def test_classify_car_control():
    res = classify_intent("شغل التكييف على درجة 22")
    assert res["intent"] == "car_control"
    assert res["entities"].get("target") == "ac"

def test_classify_chitchat():
    res = classify_intent("كيف حالك اليوم؟")
    assert res["intent"] == "chitchat"

def test_classify_general_knowledge():
    res = classify_intent("كم المسافة بين الأرض والقمر؟")
    assert res["intent"] == "general_knowledge"
```

- [ ] **Step 2: تشغيل الاختبار والتحقق من فشله**
Run: `python -m pytest tests/test_nlu_classifier.py -v`

- [ ] **Step 3: كتابة كود معالج النصوص ومصنف النوايا**
إنشاء `android/app/src/main/python/nlu_classifier.py` يتضمن:
- دالة `normalize_arabic` لإزالة التشكيل وتوحيد الألف، الياء، والتاء المربوطة.
- قواميس الكلمات المفتاحية ومرادفات اللهجات (فصحى، خليجية، شامية، عراقية) الخاصة بالسيارة.
- استخراج الكيانات `entities` (أهداف التحكم: تكييف، نوافذ، صوت، إضاءة، خرائط، مع القيم الرقمية لدرجات الحرارة أو الصوت).
- تصنيف النية بمرونة عالية بين الفئات الثلاث.

- [ ] **Step 4: تشغيل الاختبار والتحقق من نجاحه**
Run: `python -m pytest tests/test_nlu_classifier.py -v`

- [ ] **Step 5: الالتزام (Commit)**
```bash
git add tests/test_nlu_classifier.py android/app/src/main/python/nlu_classifier.py
git commit -m "feat(nlu): implement Arabic text normalization and intent classifier"
```

---

### Task 2: ذاكرة السياق وإدارة الحالات (FSM Memory & Coreference Resolution)

**Files:**
- Create: `android/app/src/main/python/fsm_memory.py`
- Test: `tests/test_fsm_memory.py`

**Interfaces:**
- Consumes: `nlu_classifier.normalize_arabic`
- Produces:
  - `class FSMMemory`:
    - `update(user_text: str, intent_data: dict, response_data: dict)`
    - `resolve_references(user_text: str) -> str`
    - `get_last_topic() -> dict`
    - `reset()`

- [ ] **Step 1: كتابة الاختبار الفاشل**
```python
# tests/test_fsm_memory.py
from fsm_memory import FSMMemory

def test_fsm_pronoun_resolution():
    memory = FSMMemory()
    # Turn 1
    memory.update("كم الساعة في باريس؟", {"intent": "general_knowledge", "entities": {"location": "باريس"}}, {})
    # Turn 2 with pronoun/locative reference
    resolved = memory.resolve_references("ما هو الطقس هناك؟")
    assert "باريس" in resolved

def test_fsm_car_adjustment_context():
    memory = FSMMemory()
    memory.update("شغل التكييف", {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}}, {})
    resolved = memory.resolve_references("خليه أبرد")
    assert "تكييف" in resolved
```

- [ ] **Step 2: تشغيل الاختبار والتأكد من فشله**
Run: `python -m pytest tests/test_fsm_memory.py -v`

- [ ] **Step 3: كتابة كود وحدة الذاكرة FSM**
إنشاء `android/app/src/main/python/fsm_memory.py` لدعم تعقب السياق، وحل الكلمات الإشارية ("هناك"، "فيها"، "له"، "نفسه"، "خليه")، وحفظ حالة آخر تفاعل مع انتهاء صلاحية السياق (Timeout).

- [ ] **Step 4: تشغيل الاختبار والتحقق من نجاحه**
Run: `python -m pytest tests/test_fsm_memory.py -v`

- [ ] **Step 5: الالتزام (Commit)**
```bash
git add tests/test_fsm_memory.py android/app/src/main/python/fsm_memory.py
git commit -m "feat(memory): implement FSM context memory and coreference resolver"
```

---

### Task 3: محرك السوالف وبيانات Kaggle العربية (Branch C: Chitchat Engine & Kaggle Script)

**Files:**
- Create: `android/app/src/main/python/chitchat_engine.py`
- Create: `android/app/src/main/assets/chitchat.json`
- Create: `scripts/fetch_kaggle_chitchat.py`
- Test: `tests/test_chitchat_engine.py`

**Interfaces:**
- Produces:
  - `class ChitchatEngine`:
    - `get_response(query: str, threshold: float = 0.6) -> str | None`
  - `scripts/fetch_kaggle_chitchat.py`:
    - جلب وتنسيق حزم الحوارات العربية من Kaggle وتحويلها إلى `chitchat.json`.

- [ ] **Step 1: كتابة الاختبار الفاشل**
```python
# tests/test_chitchat_engine.py
from chitchat_engine import ChitchatEngine

def test_chitchat_exact_and_fuzzy_match():
    engine = ChitchatEngine()
    # Exact
    ans = engine.get_response("من أنت؟")
    assert ans is not None
    assert len(ans) > 0
    # Fuzzy match with slight variation
    ans_fuzzy = engine.get_response("مين انت يا مساعد")
    assert ans_fuzzy is not None
```

- [ ] **Step 2: تشغيل الاختبار والتأكد من فشله**
Run: `python -m pytest tests/test_chitchat_engine.py -v`

- [ ] **Step 3: تجهيز chitchat.json ومحرك ChitchatEngine وسكربت Kaggle**
- كتابة قاعدة بيانات `chitchat.json` تحوي مصفوفة من الأنماط والردود الطبيعية المتنوعة (تحايا، ردود شكر، نكات، تعريف بالنفس، أسئلة السائق).
- تنفيذ `chitchat_engine.py` باستخدام خوارزمية مطابقة النصوص التقريبية (Fuzzy Matching عبر Levenshtein / SequenceMatcher).
- كتابة `scripts/fetch_kaggle_chitchat.py` لجلب وتنظيم مجموعات بيانات الشات بوت العربية من Kaggle API ودمجها في قاعدة الردود.

- [ ] **Step 4: تشغيل الاختبار والتحقق من نجاحه**
Run: `python -m pytest tests/test_chitchat_engine.py -v`

- [ ] **Step 5: الالتزام (Commit)**
```bash
git add android/app/src/main/assets/chitchat.json android/app/src/main/python/chitchat_engine.py scripts/fetch_kaggle_chitchat.py tests/test_chitchat_engine.py
git commit -m "feat(chitchat): implement Arabic chitchat engine with fuzzy matching and Kaggle dataset script"
```

---

### Task 4: عملاء الـ APIs للمعرفة العامة والطقس (Branch B: General Knowledge & APIs)

**Files:**
- Create: `android/app/src/main/python/api_clients.py`
- Test: `tests/test_api_clients.py`

**Interfaces:**
- Produces:
  - `query_wolfram(query: str, app_id: str = "") -> str`
  - `query_duckduckgo(query: str) -> str`
  - `query_weather(city: str, lat: float = None, lon: float = None) -> str`
  - `query_news(topic: str = "", country: str = "sa") -> str`
  - `query_time(city_or_timezone: str) -> str`
  - `handle_general_knowledge(query: str, entities: dict) -> str`

- [ ] **Step 1: كتابة الاختبار الفاشل**
```python
# tests/test_api_clients.py
from api_clients import format_weather_response, format_time_response, handle_general_knowledge

def test_weather_formatter():
    mock_data = {"temperature": 28.5, "weathercode": 0, "windspeed": 12.0}
    res = format_weather_response("الرياض", mock_data)
    assert "28" in res
    assert "الرياض" in res

def test_time_formatter():
    res = format_time_response("دبي", "2026-10-06T14:30:00+04:00")
    assert "14:30" in res or "2:30" in res

def test_offline_fallback():
    # If network fails, return graceful Arabic message
    res = handle_general_knowledge("ما هو الطقس في القاهرة؟", entities={}, force_offline=True)
    assert "إنترنت" in res or "شبكة" in res
```

- [ ] **Step 2: تشغيل الاختبار والتأكد من فشله**
Run: `python -m pytest tests/test_api_clients.py -v`

- [ ] **Step 3: كتابة كود api_clients.py**
تطبيق عملاء REST APIs:
- `query_open_meteo`: مع دعم المدن العربية وترجمة الإحداثيات وحالات الطقس للعربية.
- `query_world_time`: استخراج الوقت وتنسيقه للعربية.
- `query_duckduckgo`: استخلاص الموجز والتعريف وتلخيصه.
- `query_wolfram_alpha`: للحقائق والمعادلات الرياضية.
- `query_newsapi`: لجلب أحدث الأخبار وإيجازها.
- معالجة انقطاع الاتصال (Graceful Offline Handling) دون رمي استثناءات مسببة لانهيار التطبيق.

- [ ] **Step 4: تشغيل الاختبار والتحقق من نجاحه**
Run: `python -m pytest tests/test_api_clients.py -v`

- [ ] **Step 5: الالتزام (Commit)**
```bash
git add android/app/src/main/python/api_clients.py tests/test_api_clients.py
git commit -m "feat(api): implement REST API clients for knowledge, weather, news, and time"
```

---

### Task 5: الموجه الرئيسي وسكربت المحاكاة والاختبار (Master Router & Test CLI)

**Files:**
- Create: `android/app/src/main/python/car_commands.py`
- Create: `android/app/src/main/python/router.py`
- Create: `scripts/test_router_cli.py`
- Test: `tests/test_router.py`

**Interfaces:**
- Consumes: `nlu_classifier`, `fsm_memory`, `chitchat_engine`, `api_clients`
- Produces:
  - `process_voice_input(raw_text: str) -> str` (JSON string for Android bridge):
    ```json
    {
      "status": "success",
      "intent": "car_control|chitchat|general_knowledge",
      "spoken_response": "النص الصوتي المراد نطقه",
      "car_action": {
        "command": "SET_AC_TEMP",
        "parameters": {"value": 22}
      } | null
    }
    ```

- [x] **Step 1: كتابة الاختبار الفاشل**
```python
# tests/test_router.py
import json
from router import VoiceAssistantRouter

def test_full_pipeline_car():
    router = VoiceAssistantRouter()
    out = json.loads(router.process("شغل المكيف على 20"))
    assert out["intent"] == "car_control"
    assert out["car_action"]["command"] in ["SET_AC_TEMP", "AC_ON"]
    assert "20" in out["spoken_response"] or "تكييف" in out["spoken_response"]

def test_full_pipeline_chitchat():
    router = VoiceAssistantRouter()
    out = json.loads(router.process("مرحبا، صباح الخير"))
    assert out["intent"] == "chitchat"
    assert len(out["spoken_response"]) > 0

def test_multi_turn_pipeline():
    router = VoiceAssistantRouter()
    _ = router.process("كم الساعة في مكة؟")
    out2 = json.loads(router.process("وكيف الطقس هناك؟"))
    assert out2["intent"] == "general_knowledge"
```

- [x] **Step 2: تشغيل الاختبار والتأكد من فشله**
Run: `python -m pytest tests/test_router.py -v`

- [x] **Step 3: كتابة كود router.py و car_commands.py و test_router_cli.py**
- ربط مسارات المعالجة: `Listen -> Normalize -> Resolve Context -> Classify -> Branch A/B/C -> Update Memory -> Produce Output JSON`.
- توفير سكربت `test_router_cli.py` تفاعلي لتجربة الأوامر بالصوت/الكتابة مباشرة من سطر الأوامر.

- [x] **Step 4: تشغيل الاختبار والتحقق من نجاحه**
Run: `python -m pytest tests/test_router.py -v`

- [x] **Step 5: الالتزام (Commit)**
```bash
git add android/app/src/main/python/car_commands.py android/app/src/main/python/router.py scripts/test_router_cli.py tests/test_router.py
git commit -m "feat(router): implement unified VoiceAssistantRouter and interactive CLI tester"
```

---

### Task 6: مشروع أندرويد لـ BYD DiLink وربط Chaquopy و CarControlBridge

**Files:**
- Create: `android/build.gradle`
- Create: `android/settings.gradle`
- Create: `android/app/build.gradle`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/com/byd/voiceassistant/CarControlBridge.kt`
- Create: `android/app/src/main/java/com/byd/voiceassistant/TTSEngine.kt`
- Create: `android/app/src/main/java/com/byd/voiceassistant/MainActivity.kt`

**Interfaces:**
- Consumes: Chaquopy (`com.chaquo.python`) لاستدعاء `router.process_voice_input`
- Produces:
  - تطبيق Android Studio كامل مع كود Kotlin للتحكم بسيارة BYD DiLink
  - واجهة تحكم Push-to-Talk أنيقة مصممة لشاشات السيارات الأفقية والعمودية الدوارة (BYD Rotating Screen)

- [ ] **Step 1: بناء ملفات إعداد Gradle و Chaquopy و AndroidManifest**
- إعداد `build.gradle` و `app/build.gradle` لدعم Kotlin و Chaquopy وتضمين اعتمادات أندرويد و Vosk.
- إعداد `AndroidManifest.xml` مع أذونات الميكروفون، والشبكة، وشاشات DiLink الدوارة.

- [ ] **Step 2: كتابة كود CarControlBridge.kt**
تنفيذ دوال التحكم لسيارة BYD DiLink:
- `handleCarAction(command: String, params: Map<String, Any>)`
- التكييف (`AC_ON`, `AC_OFF`, `SET_AC_TEMP`, `FAN_SPEED`)
- النوافذ وفتحة السقف (`OPEN_WINDOWS`, `CLOSE_WINDOWS`, `SUNROOF`)
- الوسائط ومستوى الصوت (`VOLUME_UP`, `VOLUME_DOWN`, `MEDIA_PLAY_PAUSE`, `MEDIA_NEXT`)
- الملاحة والتطبيقات (`OPEN_MAPS`, `OPEN_APP`, `DI_LINK_SETTINGS`)

- [ ] **Step 3: كتابة كود TTSEngine.kt و MainActivity.kt**
- `TTSEngine.kt`: مشغل الصوت المحلي باللغة العربية مع دعم سرعة النطق ونبرة الصوت المناسبة للسيارة.
- `MainActivity.kt`: تهيئة بيئة Chaquopy، واجهة مستخدم Push-to-Talk كبيرة وسريعة الاستجابة، استقبال الصوت، وتمريره للبايثون، وتنفيذ أمر السيارة ونطق الرد.

- [ ] **Step 4: الالتزام (Commit)**
```bash
git add android/
git commit -m "feat(android): implement BYD DiLink Android app with Chaquopy, CarControlBridge, and UI"
```

---

### Task 7: توثيق المشروع والتهيئة للنشر على GitHub (Docs & Git Repository)

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `docs/BYD_DILINK_DEPLOYMENT.md`

- [ ] **Step 1: كتابة ملف .gitignore الشامل**
تضمين استثناءات Gradle، بيئات Python الافتراضية، ملفات الـ Cache، ونماذج الصوت الكبيرة.

- [ ] **Step 2: كتابة README.md الشامل ووثيقة النشر**
- شرح المعمارية ومخطط التدفق.
- خطوات التثبيت والتشغيل والتجربة عبر CLI.
- خطوات بناء ملف الـ APK في Android Studio وتثبيته على شاشة BYD DiLink عبر فلاش ميموري (USB) أو ADB.
- أوامر Git الدقيقة لإنشاء مستودع جديد على GitHub ورفع المشروع.

- [ ] **Step 3: فحص الحالة والالتزام النهائي (Final Commit)**
```bash
git add .gitignore README.md docs/BYD_DILINK_DEPLOYMENT.md
git commit -m "docs: add comprehensive README, deployment guide, and gitignore"
```
