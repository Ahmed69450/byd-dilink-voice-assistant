# مساعد سيارات BYD DiLink الصوتي الذكي
# BYD DiLink Arabic Voice Assistant

[![Platform](https://img.shields.io/badge/Platform-BYD%20DiLink%203.0%20%7C%204.0%20%7C%205.0-blue.svg)](https://github.com)
[![Android](https://img.shields.io/badge/Android-SDK%2028+-green.svg)](https://developer.android.com)
[![Python](https://img.shields.io/badge/Python-3.8+-brightgreen.svg)](https://www.python.org)
[![Engine](https://img.shields.io/badge/Chaquopy-15.0.1-orange.svg)](https://chaquo.com/chaquopy/)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-165%20Passing-success.svg)](tests/)
[![Download APK](https://img.shields.io/badge/Download-APK%20v1.0.0-success?style=for-the-badge&logo=android)](https://github.com/Ahmed69450/byd-dilink-voice-assistant/releases/download/v1.0.0/BYD-DiLink-VoiceAssistant-v1.0.0.apk)


---

## الفهرس العربي (Arabic Table of Contents)
1. [نظرة عامة على المشروع](#نظرة-عامة-على-المشروع)
2. [المعمارية ومخطط التدفق الشامل](#المعمارية-ومخطط-التدفق-الشامل)
3. [المسارات الثلاثة للنظام (The Three Branches)](#المسارات-الثلاثة-للنظام-the-three-branches)
4. [المتطلبات الأساسية والتثبيت](#المتطلبات-الأساسية-والتثبيت)
5. [أداة التشخيص والاختبار السريع عبر موجه الأوامر (CLI)](#أداة-التشخيص-والاختبار-السريع-عبر-موجه-الأوامر-cli)
6. [خطوات بناء حزمة التطبيق (APK Build)](#خطوات-بناء-حزمة-التطبيق-apk-build)
7. [إثراء قاعدة السوالف عبر مجموعات بيانات Kaggle](#إثراء-قاعدة-السوالف-عبر-مجموعات-بيانات-kaggle)
8. [إعداد مفاتيح واجهات برمجة التطبيقات (API Keys)](#إعداد-مفاتيح-واجهات-برمجة-التطبيقات-api-keys)
9. [أوامر النشر على مستودع GitHub](#أوامر-النشر-على-مستودع-github)
10. [دليل التثبيت على شاشة السيارة](#دليل-التثبيت-على-شاشة-السيارة)

---

## English Table of Contents
1. [Project Overview](#english-overview)
2. [System Architecture](#system-architecture)
3. [The Three Execution Branches](#the-three-execution-branches)
4. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
5. [CLI Diagnostics & Simulation](#cli-diagnostics--simulation)
6. [Building the Android APK](#building-the-android-apk)
7. [Kaggle Dataset Enrichment Pipeline](#kaggle-dataset-enrichment-pipeline)
8. [API Key Configuration](#api-key-configuration)
9. [Git & GitHub Repository Deployment](#git--github-repository-deployment)

---

# 🇸🇦 القسم العربي (Arabic Section)

## 📌 نظرة عامة على المشروع
مساعد صوتي ذكي فائق السرعة وخفيف الوزن مخصص لشاشات سيارات **BYD DiLink** (Atto 3, Han, Tang, Seal, Dolphin وغيرها). 
يتميز النظام بعدم اعتماده على النماذج التوليدية الضخمة (No Heavy LLMs) لضمان العمل اللحظي دون تأخير واستهلاك الموارد، حيث يجمع بين واجهة ونظام تشغيل أندرويد بـ **Kotlin** ومحرك توجيه لغوي متقدم بـ **Python** عبر **Chaquopy**، مع دعم كامل للعمل بدون إنترنت للوظائف الأساسية (Offline-First).

---

## 🏛 المعمارية ومخطط التدفق الشامل

```
                    ┌─────────────────────────────────────────┐
                    │      شاشة وواجهة BYD DiLink (Kotlin)     │
                    │         زر التحدث (Push-to-Talk)        │
                    └────────────────────┬────────────────────┘
                                         │ إشارة الميكروفون
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │       محرك Vosk STT (Offline Arabic)    │
                    │        تحويل الصوت إلى نص عربي          │
                    └────────────────────┬────────────────────┘
                                         │ نص الأمر
                                         ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │               محرك بايثون المدمج عبر Chaquopy (Router & NLU)                │
 │                                                                             │
 │  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  │
 │  │      مصنف النوايا المتقدم       │   │      ذاكرة السياق متعدد الأدوار │  │
 │  │   (NLU Intent Classifier)       │◄─►│        (FSM Context Memory)     │  │
 │  │   تطبيع النص وقواعد اللهجات     │   │     حل الضمائر وإشارات المكان   │  │
 │  └─────────────────┬───────────────┘   └─────────────────────────────────┘  │
 │                    │                                                        │
 │         ┌──────────┴───────────────┬─────────────────────────┐              │
 │         ▼                          ▼                         ▼              │
 │    [المسار A]                  [المسار B]                [المسار C]         │
 │   أوامر السيارة              المعرفة العامة                السوالف          │
 │ (Offline Car Control)      (REST APIs & Math)         (Arabic Chitchat)     │
 └─────────┬──────────────────────────┬─────────────────────────┬──────────────┘
           │ أمر JSON                 │ نص الإجابة              │ نص الرد الودي
           ▼                          └────────────┬────────────┘
 ┌───────────────────────────────────┐             │
 │      جسر سيارات BYD DiLink        │             │ النص النهائي المنطوق
 │      (CarControlBridge.kt)        │             ▼
 │ تكييف • نوافذ • أنوار • صوتيات • تطبيقات │  ┌─────────────────────────────────────┐
 └───────────────────────────────────┘  │     محرك النطق الصوتي (TTS Engine)  │
                                        │      نطق محلي باللغة العربية        │
                                        └──────────────────┬──────────────────┘
                                                           │ صوت واضح
                                                           ▼
                                        ┌─────────────────────────────────────┐
                                        │          سماعات سيارة BYD           │
                                        │     مع خفض صوت الراديو تلقائياً     │
                                        └─────────────────────────────────────┘
```

---

## 🚦 المسارات الثلاثة للنظام (The Three Branches)

### 1. المسار A: أوامر السيارة المحلية (Branch A - Offline Car Controls)
- **طبيعة العمل:** محلي 100% دون الحاجة إلى شبكة الإنترنت وبسرعة استجابة فورية (أقل من 30 مللي ثانية).
- **الأنظمة المدعومة:**
  - **التكييف (AC):** تشغيل/إيقاف، ضبط درجة الحرارة برقم محدد، رفع/خفض الحرارة، والتحكم بسرعة المروحة.
  - **النوافذ وفتحة السقف:** فتح وإغلاق النوافذ كلياً أو جزئياً، فتح وإغلاق فتحة السقف وستارة السقف.
  - **الإضاءة والأنوار:** تشغيل وإطفاء الأنوار والمصابيح، إضاءة القراءة، والمصابيح الترحيبية والمحيطية.
  - **الوسائط ومستوى الصوت:** كتم الصوت، رفع/خفض الصوت، ضبط مستوى رقمي محدد، إيقاف وتشغيل الوسائط، والتنقل بين المقاطع.
  - **التطبيقات والملاحة:** فتح تطبيقات النظام الأصلية (الكاميرات المحيطية 360، تطبيق الطاقة، الإعدادات، وخرائط الملاحة إلى وجهة محددة).
- **آلية الربط:** يرسل محرك البايثون كائناً بصيغة JSON إلى `CarControlBridge.kt` الذي ينفذ نية النظام المناسبة عبر `AudioManager` أو نوايا بث السيارة (`System Broadcast Intents`).

### 2. المسار B: المعرفة العامة على غرار أليكسا (Branch B - Alexa-like Knowledge APIs)
- **طبيعة العمل:** استعلامات سحابية ذكية عبر واجهات برمجة تطبيقات خفيفة وسريعة، مع حماية كاملة عند انقطاع الإنترنت (Offline Fallback).
- **الخدمات المدعومة:**
  - **Wolfram Alpha API:** حل العمليات الرياضية المعقدة، والتحويلات، والحقائق العلمية الدقيقة.
  - **DuckDuckGo Instant Answers:** تعريفات الشخصيات والمفاهيم والمصطلحات التاريخية والعامة.
  - **Open-Meteo API:** استعلام مباشر عن حالة الطقس، درجات الحرارة، وسرعة الرياح لجميع المدن العربية والعالمية.
  - **World Time API:** معرفة الوقت والتاريخ الدقيق لأي منطقة زمنية أو مدينة.
  - **NewsAPI:** استرجاع أهم الأخبار اليومية العاجلة.
- **الحماية عند غياب الاتصال:** في حال عدم توفر شريحة اتصال أو فقدان إشارة الشبكة أثناء القيادة، يعتذر المساعد بلباقة مع توضيح أن أوامر السيارة المحلية تعمل بكفاءة.

### 3. المسار C: محرك السوالف والردود الودية (Branch C - Arabic Chitchat Engine)
- **طبيعة العمل:** محلي بالكامل دون إنترنت، معتمد على قاعدة بيانات غنية مهيأة مسبقاً (`chitchat.json`).
- **الخوارزمية:** مطابقة تقريبية ذكية (Fuzzy Matching) معتمدة على مسافة ليفنشتاين (Levenshtein Distance) مع عتبة ثقة محددة، تتيح فهم مختلف اللهجات (الخليجية، المصرية، الشامية) والأخطاء الإملائية.
- **إثراء البيانات:** مزود بأداة برمجية متكاملة لجلب ومعالجة مجموعات البيانات الحوارية من Kaggle أو ملفات CSV/TSV/JSON المحلية.

---

## 📋 المتطلبات الأساسية والتثبيت

### بيئة التطوير (Prerequisites):
- **نظام التشغيل:** Windows 10/11، macOS، أو Linux.
- **Python:** إصدار **3.8** فما فوق (موصى بـ 3.10 أو 3.11 أو 3.12).
- **Java:** إصدار **Java 17 (JDK 17)**.
- **Android Studio:** إصدار Hedgehog (2023.1.1) أو Iguana أو Koala أو أعلى.
- **Android SDK:** إصدار الحد الأدنى **minSdkVersion 28** (Android 9.0) والإصدار المستهدف **targetSdkVersion 34** (Android 14).

### تثبيت مكتبات بايثون المحلية:
```bash
# إنشاء بيئة افتراضية اختيارية وتفعيلها
python -m venv venv
# لنظام ويندوز:
venv\Scripts\activate
# لنظام لينكس/ماك:
source venv/bin/activate

# تثبيت الاعتماديات المطلوبة للاختبارات والمزامنة
pip install pytest requests
```

---

## 💻 أداة التشخيص والاختبار السريع عبر موجه الأوامر (CLI)

يتضمن المشروع سكربت CLI مخصص لاختبار كافة إمكانيات المساعد وحوارات السياق المتعددة دون الحاجة لفتح محاكي أندرويد:

```bash
# 1. تشغيل السيناريو التوضيحي الآلي الكامل (Demo Scenario)
python scripts/test_router_cli.py --demo

# 2. تشغيل الوضع التفاعلي المباشر (Interactive Driving Simulation)
python scripts/test_router_cli.py --interactive

# 3. اختبار استعلام مفرد مباشر
python scripts/test_router_cli.py --query "شغل التكييف على 22 درجة"
python scripts/test_router_cli.py --query "ما هو الطقس في الرياض؟"
python scripts/test_router_cli.py --query "كم الساعة الآن في دبي؟"
python scripts/test_router_cli.py --query "من أنت وماذا تستطيع أن تفعل؟"
```

### تشغيل حزمة الفحص الشاملة (159 اختباراً):
```bash
python -m pytest tests/ -v
```

---

## 📦 خطوات بناء حزمة التطبيق (APK Build)

### الطريقة الأولى: عبر سطر الأوامر (Gradle CLI)
من المجلد الرئيسي للمشروع:
```bash
# على أنظمة Windows:
cd android
.\gradlew.bat assembleRelease

# على أنظمة Linux أو macOS:
cd android
chmod +x gradlew
./gradlew assembleRelease
```
ستجد ملف الحزمة الناتج في المسار:
`android/app/build/outputs/apk/release/app-release.apk`

### الطريقة الثانية: عبر Android Studio
1. افتح بيئة Android Studio واختر **Open Existing Project**.
2. حدد مجلد `android` داخل المشروع.
3. انتظر انتهاء مزامنة ملفات Gradle وتهيئة مكونات Chaquopy.
4. من القائمة العلوية: **Build > Build Bundle(s) / APK(s) > Build APK(s)**.

---

## 📊 إثراء قاعدة السوالف عبر مجموعات بيانات Kaggle

يحتوي مجلد `scripts/` على أداة `fetch_kaggle_chitchat.py` المتخصصة في تنزيل وتنظيف ودمج مجموعات البيانات الحوارية العربية:

```bash
# تنزيل مجموعة بيانات من Kaggle ودمجها مع قاعدة بيانات التطبيق:
python scripts/fetch_kaggle_chitchat.py --dataset "username/arabic-dialogue-dataset" --merge

# استيراد ومعالجة ملف حوارات محلي (CSV أو JSON أو TSV):
python scripts/fetch_kaggle_chitchat.py --local-file path/to/dataset.csv --merge

# تنظيف وحفظ النتيجة في ملف مخصص:
python scripts/fetch_kaggle_chitchat.py --local-file raw_dialogues.tsv --output android/app/src/main/assets/chitchat.json
```

---

## 🔑 إعداد مفاتيح واجهات برمجة التطبيقات (API Keys)

الخدمات التي لا تتطلب مفاتيح (تعمل مباشرة ومجاناً):
- **Open-Meteo:** حالة الطقس وإحداثيات المدن.
- **DuckDuckGo Instant Answers:** الحقائق العامة والتعريفات.
- **World Time API:** التوقيت العالمي والمناطق الزمنية.

الخدمات التي تدعم مفاتيح اختيارية للمعرفة المتقدمة:
- **Wolfram Alpha:** للعمليات الرياضية والاستعلامات الفلكية والعلمية.
- **NewsAPI:** لعناوين الأخبار العالمية والعربية.

### ضبط المفاتيح عبر متغيرات البيئة:
```bash
# على ويندوز (PowerShell):
$env:WOLFRAM_APP_ID="YOUR_WOLFRAM_KEY"
$env:NEWS_API_KEY="YOUR_NEWSAPI_KEY"

# على لينكس/ماك:
export WOLFRAM_APP_ID="YOUR_WOLFRAM_KEY"
export NEWS_API_KEY="YOUR_NEWSAPI_KEY"
```

أو عبر تمريرها برمجياً من خلال كائن التهيئة `config` إلى دالة `VoiceAssistantRouter`.

---

## 🚀 أوامر النشر على مستودع GitHub

لإنشاء ورفع هذا المشروع بالكامل إلى مستودعك الخاص على GitHub، اتبع الخطوات التالية في الطرفية:

```bash
# 1. إضافة جميع ملفات المشروع المهيأة (المستثناة تلقائياً عبر .gitignore)
git add .

# 2. إنشاء الالتزام الشامل للنظام
git commit -m "feat: complete BYD DiLink voice assistant system"

# 3. التأكد من تسمية الفرع الرئيسي بـ main
git branch -M main

# 4. ربط المشروع بمستودع GitHub الجديد الخاص بك (استبدل اسم المستخدم)
git remote add origin https://github.com/<USERNAME>/byd-dilink-voice-assistant.git

# 5. رفع الكود إلى المستودع البعيد
git push -u origin main
```

---

## 🚗 دليل التثبيت على شاشة السيارة

للحصول على الدليل الكامل والخطوات المصورة لتفعيل خيارات المطور في شاشات BYD، نقل ملف الـ APK عبر فلاشة USB أو عبر شبكة Wi-Fi باستخدام ADB، وضبط سلوك دوران الشاشة ومصفوفة الميكروفونات، يُرجى مراجعة الوثيقة المخصصة:
👉 **[دليل تشغيل ونشر BYD DiLink التفصيلي (docs/BYD_DILINK_DEPLOYMENT.md)](docs/BYD_DILINK_DEPLOYMENT.md)**

---
---

# 🇬🇧 English Section

## 💡 English Overview
**BYD DiLink Arabic Voice Assistant** is an ultra-fast, zero-LLM intelligent in-car voice system built specifically for BYD DiLink automotive infotainment hardware (Atto 3, Han, Tang, Seal, Dolphin, etc.). 
Operating on an offline-first architecture, the application pairs an Android native host layer (**Kotlin**) with an embedded **Python** NLU router powered by **Chaquopy 15.0.1**.

---

## 🏛 System Architecture

The system pipeline routes voice queries into three execution branches:

1. **Host UI & Capture (Android Kotlin):** Push-to-Talk activation, managing audio focus ducking over car radio/media.
2. **Offline STT (Vosk Engine):** Local Arabic speech recognition using a compact acoustic model (`vosk-model-small-ar-0.22`).
3. **NLU & Router Engine (Python via Chaquopy):**
   - **Text Normalizer:** Strips Arabic diacritics, normalizes Alef/Yaa/Taa-Marbuta, and parses written Arabic numeral words.
   - **FSM Context Memory:** Maintains multi-turn dialog state, resolves locative pronouns ("هناك" / "over there") and relative car adjustments ("خليه أبرد" / "make it colder").
   - **Intent Classifier:** Dispatches utterances to Branch A, B, or C.

```
[Driver PTT Voice] -> [Vosk Offline STT] -> [Python Router & NLU]
                                                     │
              ┌──────────────────────────────────────┼──────────────────────────────────────┐
              ▼                                      ▼                                      ▼
      [Branch A: Car Control]              [Branch B: Knowledge]                    [Branch C: Chitchat]
     • AC & Fan Speed                     • Open-Meteo (Weather)                   • Fuzzy Matching
     • Windows & Sunroof                  • Wolfram Alpha (Math/Facts)             • Dialectal Persona
     • Vehicle Lighting                   • DuckDuckGo (Abstracts)                 • Pre-bundled Dataset
     • Volume & Media Playback            • World Time API & NewsAPI               • Kaggle Ingestion Pipeline
     • System Navigation & Apps           │                                        │
               │                          │                                        │
               ▼                          └──────────────────┬─────────────────────┘
    [CarControlBridge.kt]                                    ▼
 (System Broadcasts & AudioManager)             [Native/Piper Arabic TTS]
                                                             ▼
                                                  [Vehicle Speakers]
```

---

## 🚦 The Three Execution Branches

- **Branch A (Offline Car Controls):** 100% offline with zero external network dependency. Returns structured JSON executed by `CarControlBridge.kt` via native Android system intents, media keycodes, and audio manager calls.
  - **Climate Control (HVAC):** Power on/off, precise temperature targets, incremental heating/cooling, and fan blower speeds.
  - **Windows & Sunroof:** Full/partial open/close for all windows or individual driver window, sunroof glass, and sunshade.
  - **Vehicle Lighting:** Headlights, ambient cabin lighting, and interior reading lights activation and deactivation.
  - **Media & Volume:** Mute toggle, discrete volume levels, step volume, media playback, pause, and track skip.
  - **Navigation & DiLink Apps:** Direct navigation intents, map launches, 360 panoramic cameras, energy management, and car settings.
- **Branch B (Alexa-like Knowledge APIs):** Connects to lightweight REST endpoints (Open-Meteo, DuckDuckGo Instant Answers, Wolfram Alpha, World Time API, and NewsAPI) with complete offline fallback protection.
- **Branch C (Arabic Chitchat Engine):** Sub-50ms fuzzy matching against pre-curated Egyptian, Gulf, and MSA conversation pairs in `chitchat.json`, extendable via Kaggle dataset scripts.

---

## 🛠 Prerequisites & Environment Setup

- **Java JDK:** Version 17
- **Android Studio:** Hedgehog (2023.1.1) or newer
- **Android SDK:** `minSdk` 28, `targetSdk` 34
- **Python:** 3.8+ (requests, pytest)

```bash
# Install Python test dependencies
pip install pytest requests
```

---

## 💻 CLI Diagnostics & Simulation

Simulate full multi-turn car driving scenarios directly from your workstation:

```bash
# Automated multi-turn demo scenario
python scripts/test_router_cli.py --demo

# Interactive REPL simulator
python scripts/test_router_cli.py --interactive

# Single utterance query
python scripts/test_router_cli.py --query "شغل التكييف على 20"
```

Run unit and integration test suite:
```bash
python -m pytest tests/ -v
```

---

## 📦 Building the Android APK

Build via Gradle command line:
```bash
# Windows
cd android
.\gradlew.bat assembleRelease

# Linux / macOS
cd android
chmod +x gradlew
./gradlew assembleRelease
```
Output APK location: `android/app/build/outputs/apk/release/app-release.apk`

---

## 📊 Kaggle Dataset Enrichment Pipeline

Fetch, clean, normalize, and format public Arabic conversational datasets from Kaggle:

```bash
python scripts/fetch_kaggle_chitchat.py --dataset "username/arabic-dialogue" --merge
python scripts/fetch_kaggle_chitchat.py --local-file sample.csv --merge
```

---

## 🔑 API Key Configuration

Optional API keys for Wolfram Alpha and NewsAPI can be supplied via environment variables:

```bash
# Windows PowerShell
$env:WOLFRAM_APP_ID="YOUR_APP_ID"
$env:NEWS_API_KEY="YOUR_API_KEY"

# Linux / macOS
export WOLFRAM_APP_ID="YOUR_APP_ID"
export NEWS_API_KEY="YOUR_API_KEY"
```

---

## 🚀 Git & GitHub Repository Deployment

Deploy to a brand-new GitHub repository using the following sequence:

```bash
git add .
git commit -m "feat: complete BYD DiLink voice assistant system"
git branch -M main
git remote add origin https://github.com/<USERNAME>/byd-dilink-voice-assistant.git
git push -u origin main
```

For hardware setup, USB debugging, Vosk model installation, and rotation behavior on BYD screens, refer to **[BYD DiLink Deployment Guide](docs/BYD_DILINK_DEPLOYMENT.md)**.
