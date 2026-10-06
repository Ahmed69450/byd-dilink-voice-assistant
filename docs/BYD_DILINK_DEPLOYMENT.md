# دليل تشغيل وتثبيت المساعد الصوتي على شاشات BYD DiLink
# BYD DiLink Voice Assistant - Vehicle Deployment & Installation Manual

---

## 1. نبذة عامة والتوافق (Overview & Hardware Compatibility)

تم تصميم هذا المساعد الصوتي خصيصاً للعمل على شاشات سيارات **BYD DiLink** الذكية بمختلف أجيالها. يعمل التطبيق كوحدة متكاملة تجمع بين بيئة Android الأصلية (Kotlin) ومحرك معالجة اللغات الطبيعية (Python via Chaquopy) مع دعم كامل للتشغيل بدون إنترنت (Offline-First).

### الأجهزة والأنظمة المدعومة (Supported Hardware & Systems):

| جيل DiLink | إصدار Android الأساسي | المعالج المركزي (SoC) | طرازات BYD المتوافقة (أمثلة) | حالة الدعم |
| :--- | :--- | :--- | :--- | :--- |
| **DiLink 3.0** | Android 9.0 (Pie) / 10 | Qualcomm Snapdragon 665 / 625 | Atto 3 (الدفعات المبكرة), Qin Plus, Song Pro, Tang EV | مدعوم بالكامل (minSdk 28) |
| **DiLink 4.0 (4G/5G)** | Android 10 / 11 | Qualcomm Snapdragon 665 / 690 / 8155 | Atto 3, Han EV/DM-i, Tang DM-i, Destroyer 05, Dolphin | مدعوم بالكامل وموصى به |
| **DiLink 5.0** | Android 12 / 13 | Qualcomm Snapdragon 8155 / 8295 | BYD Seal, Song L, Denza D9/N7, Yangwang U8 | مدعوم بالكامل |

---

## 2. تفعيل خيارات المطور وتصحيح USB (Enabling Developer Options & USB Debugging)

لتثبيت حزم التطبيقات (`.apk`) أو تشخيص السجلات (`logcat`)، يجب تفعيل وضع المطور وتصحيح USB على شاشة السيارة:

### الطريقة القياسية (Standard Method):
1. شغل السيارة أو ضع مفتاح التشغيل في وضع **ACC / ON**.
2. افتح قائمة **إعدادات السيارة (Vehicle Settings)** من الشاشة الرئيسية.
3. انتقل إلى تبويب **النظام (System)** ثم **حول الشاشة / إصدار البرنامج (About System / Software Version)**.
4. ابحث عن حقل **رقم الإصدار (Build Number / Version Number)**.
5. انقر على رقم الإصدار **7 مرات متتالية وسريعة**.
6. ستظهر رسالة سريعة في أسفل الشاشة: *"أنت الآن مطور برامج!" (You are now a developer!)*.
7. ارجع خطوة واحدة للخلف؛ ستجد خياراً جديداً بعنوان **خيارات المطور (Developer Options)**.
8. ادخل إلى خيارات المطور وفعل:
   - **تصحيح أخطاء USB (USB Debugging)**.
   - **السماح بتثبيت التطبيقات عبر USB (Install via USB)** (إن وُجد).
   - **البقاء في وضع التنبيه (Stay Awake)** (اختياري، لتجنب نوم الشاشة أثناء التطوير).

### الرموز الهندسية البديلة (Engineering Codes - في حال إخفاء القائمة):
في بعض شاشات DiLink المخصصة لأسواق معينة، قد تكون القائمة مغلقة بواسطة المصنع. يمكن استخدام تطبيق الاتصال (Dialer) أو لوحة البحث في الإعدادات لإدخال الرموز التالية:
- `*#*#2846579#*#*` (تفتح قائمة ProjectMenu لاختيار USB Ports Information).
- أو عبر إعدادات لوحة المفاتيح والبحث عن "Developer Options".

> ⚠️ **تنبيه أمان وسلامة:** لا تقم بتعديل إعدادات الـ CAN Bus أو بروتوكولات الأمان الأساسية للسيارة من القائمة الهندسية. التزم فقط بتفعيل ADB وتثبيت التطبيقات المعتمدة.

---

## 3. إعداد نموذج الصوت العربي بدون إنترنت (Vosk Offline Arabic Model)

يعتمد محرك التعرف الصوتي (`STTEngine.kt`) على نموذج صوتي عربي خفيف ومدمج من **Vosk**:

### تحميل النموذج:
1. حمّل النموذج العربي المصغر الرسمي:
   - **الاسم:** `vosk-model-small-ar-0.22`
   - **الرابط:** [https://alphacephei.com/vosk/models/vosk-model-small-ar-0.22.zip](https://alphacephei.com/vosk/models/vosk-model-small-ar-0.22.zip)
   - **الحجم:** حوالي 45 ميجابايت (خفيف جداً ومثالي لذاكرة سيارات DiLink).

### وضع النموذج داخل المشروع قبل البناء:
1. فك ضغط الملف المضغوط.
2. أعد تسمية المجلد الناتج إلى `model-ar` (أو انسخ محتوياته مباشرة).
3. ضعه في المسار التالي داخل مجلد الأندرويد:
   ```text
   android/app/src/main/assets/model-ar/
   ├── am/
   ├── conf/
   │   ├── mfcc.conf
   │   └── model.conf
   ├── graph/
   │   ├── HCLG.fst
   │   ├── disambig_tid.int
   │   └── phones/
   └── ivector/
   ```
4. عند تشغيل التطبيق لأول مرة على الشاشة، سيقوم `STTEngine` بنسخ النموذج تلقائياً إلى الذاكرة التخزينية الداخلية للتطبيق عبر `StorageService.unpack(context, "model-ar", "model")` والبدء الفوري بدون إنترنت.

---

## 4. طرق تثبيت التطبيق على الشاشة (Installation Methods)

### الطريقة الأولى: التثبيت عبر وحدة تخزين USB (Flash Drive) - الأسهل والأسرع
1. بعد بناء ملف `app-release.apk` (أو `app-debug.apk`):
2. جهز وحدة تخزين USB (فلاش ميموري) مفرمتة بنظام ملفات **FAT32** أو **NTFS**.
3. انسخ ملف الـ APK إلى الجذر الرئيسي للفلاشة.
4. صل الفلاشة بالمنفذ المخصص لنقل البيانات في الكونسول الأمامي للسيارة (USB Data Port - عادة ما يكون المنفذ ذو الشعار الأبيض أو منفذ Type-C الرئيسي، وليس منفذ الشحن فقط).
5. افتح تطبيق **مدير الملفات (File Manager)** على شاشة DiLink.
6. افتح وحدة التخزين الخارجية (USB Drive) واضغط على ملف `app-release.apk`.
7. وافق على تثبيت التطبيقات من مصادر غير معروفة إذا طُلب منك ذلك، واضغط **تثبيت (Install)**.

---

### الطريقة الثانية: التثبيت عبر الشبكة اللاسلكية (ADB over Wi-Fi)
تعتبر هذه الطريقة الأنسب للمطورين لاختبار التعديلات وتحديث التطبيق دون الحاجة لفلاشة:

1. صل شاشة السيارة وجهاز الحاسوب المحمول بنفس شبكة الـ Wi-Fi (مثلاً عبر نقطة اتصال الهواتف المحمولة Personal Hotspot).
2. افتح إعدادات Wi-Fi في شاشة السيارة لمعرفة عنوان الـ IP الخاص بالشاشة (مثلاً: `192.168.43.150`).
3. على جهاز الحاسوب، افتح الطرفية (Terminal / PowerShell) ونفذ:
   ```bash
   # الاتصال بشاشة السيارة عبر المنفذ الافتراضي 5555
   adb connect 192.168.43.150:5555

   # التحقق من نجاح الاتصال
   adb devices
   ```
4. بعد ظهور السيارة كجهاز متصل (`device`)، نفذ أمر التثبيت المباشر:
   ```bash
   # تثبيت التطبيق مع استبدال النسخة السابقة والاحتفاظ بالبيانات
   adb install -r android/app/build/outputs/apk/release/app-release.apk
   ```
5. منح إذن الميكروفون برمجياً لتجنب ظهور نافذة الاستئذان أثناء القيادة:
   ```bash
   adb shell pm grant com.byd.voiceassistant android.permission.RECORD_AUDIO
   ```

---

### الطريقة الثالثة: التثبيت عبر كابل USB المباشر (ADB over USB)
1. استخدم كابل USB (Type-A to Type-A أو Type-C to Type-C متوافق مع نقل البيانات).
2. صل الكمبيوتر بمنفذ نقل البيانات الرئيسي في لوحة سيارة BYD.
3. اقبل رسالة تصريح تصحيح أخطاء USB التي ستظهر على شاشة DiLink مع تفعيل خيار "السماح دائماً من هذا الحاسوب".
4. نفذ أمر التثبيت:
   ```bash
   adb install -r android/app/build/outputs/apk/release/app-release.apk
   ```

---

## 5. ضبط الصوت والأذونات (Audio Focus & Permissions)

### 1. التركيز الصوتي وخفض الموسيقى (Audio Focus & Ducking):
- تم ضبط `CarControlBridge` ومحركات الصوت لطلب التركيز الصوتي عبر:
  ```kotlin
  AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
  ```
- **السلوك التلقائي:** عند الضغط على زر التحدث (Push-to-Talk) أو نطق المساعد الصوتي للإجابة:
  - ينخفض صوت الموسيقى أو الراديو تلقائياً (Audio Ducking) لتسهيل سماع صوت السائق.
  - ينطق المساعد الرد بوضوح عبر سماعات السيارة الأمامية.
  - فور انتهاء النطق، يعود صوت راديو/وسائط السيارة إلى مستواه السابق بانسيابية.

### 2. ميكروفون السيارة (Vehicle Microphone Matrix):
- يطلب التطبيق إذن `android.permission.RECORD_AUDIO`.
- في شاشات DiLink، ترتبط مصفوفة الميكروفونات المدمجة في السقف (Roof-mounted microphones) مباشرة بمدخل الصوت القياسي `MediaRecorder.AudioSource.MIC` أو `VOICE_RECOGNITION` مع تقليل الضوضاء المدمج بالسيارة.

---

## 6. التعامل مع الشاشة الدوارة لـ BYD (Rotating Screen Handling)

تتميز سيارات BYD بشاشة DiLink الدوارة كهربائياً (Rotatable Touchscreen) التي تدعم الوضعين الأفقي (Landscape) والعمودي (Portrait):

1. **عدم إعادة تشغيل التطبيق أثناء الدوران:**
   تم ضبط `AndroidManifest.xml` بالسمات التالية:
   ```xml
   android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize"
   ```
   هذا يضمن أنه عند تدوير الشاشة:
   - **لا يُعاد تشغيل الـ Activity** أو محرك Vosk الصوتي.
   - لا ينقطع التسجيل الصوتي أو التوليد الصوتي للمساعد.
2. **واجهة مستخدم متكيفة (Adaptive Layout):**
   - تم تصميم `activity_main.xml` باستخدام `ConstraintLayout` بنسب مئوية وعناصر متجاوبة لضمان ظهور بطاقات المحادثة وزر الميكروفون بحجم مثالي وواضح في كلا الوضعين (الأفقي 15.6 بوصة أو العمودي).

---

## 7. فحص السجلات والتشخيص أثناء التشغيل (Diagnostics & Troubleshooting)

يمكنك مراقبة استجابة الأوامر ومحركات النظام لحظياً عبر تصفية سجلات ADB:

```bash
# مراقبة كافة مكونات المساعد الصوتي
adb logcat -s BYD_CarControl BYD_STT BYD_TTS BYD_Assistant

# أو مراقبة أوامر التحكم بالسيارة المنفذة فقط
adb logcat -s BYD_CarControl
```

### المشاكل الشائعة وحلولها:

| المشكلة | السبب المحتمل | الحل السريع |
| :--- | :--- | :--- |
| **المساعد لا يستمع أو يغلق فوراً** | عدم منح إذن الميكروفون | اذهب إلى إعدادات الشاشة > التطبيقات > BYD Voice Assistant > الأذونات > الميكروفون > سماح، أو نفذ أمر `adb shell pm grant ...` المذكور أعلاه. |
| **محرك Vosk يفشل في التهيئة** | نموذج الصوت غير موجود في `assets/model-ar` | تأكد من وضع ملفات نموذج `vosk-model-small-ar-0.22` داخل مجلد الأصول قبل بناء الحزمة كما هو مشروح في القسم 3. |
| **أوامر السيارة تنفذ لكن بدون صوت رد** | محرك TTS النظامي لا يدعم اللغة العربية | التطبيق يدعم محركات TTS المتعددة؛ تأكد من تفعيل حزمة الصوت العربية في إعدادات Android (Text-to-Speech Settings > Google Speech Recognition & Synthesis / Arabic). |
| **الاستعلامات العامة تفشل** | عدم توفر اتصال بالإنترنت في شاشة السيارة | الاستعلامات العامة (الطقس، الأخبار، ويكيبيديا) تتطلب إنترنت (شريحة SIM مدمجة أو نقطة اتصال Wi-Fi). أوامر السيارة (المسار A) والمحادثات الأساسية (المسار C) تعمل 100% بدون إنترنت. |
| **تعذر الاتصال بـ ADB عبر Wi-Fi** | الشاشة والحاسوب على شبكات مختلفة أو جدار حماية | تأكد من أن الحاسوب والسيارة متصلان بنفس الشبكة تماماً (نقطة اتصال هاتف واحدة). |

---
---

# 🇬🇧 English Section: Vehicle Deployment & Installation Manual

---

## 1. Overview & Hardware Compatibility

This voice assistant is purpose-built for **BYD DiLink** smart infotainment head units across generations. It operates as a cohesive stack integrating native Android (Kotlin) with an embedded natural language engine (Python via Chaquopy) adhering to an offline-first architecture.

### Supported Hardware & Systems:

| DiLink Generation | Base Android Version | System SoC | Compatible BYD Models (Examples) | Support Status |
| :--- | :--- | :--- | :--- | :--- |
| **DiLink 3.0** | Android 9.0 (Pie) / 10 | Qualcomm Snapdragon 665 / 625 | Atto 3 (Early batches), Qin Plus, Song Pro, Tang EV | Fully Supported (minSdk 28) |
| **DiLink 4.0 (4G/5G)** | Android 10 / 11 | Qualcomm Snapdragon 665 / 690 / 8155 | Atto 3, Han EV/DM-i, Tang DM-i, Destroyer 05, Dolphin | Fully Supported & Recommended |
| **DiLink 5.0** | Android 12 / 13 | Qualcomm Snapdragon 8155 / 8295 | BYD Seal, Song L, Denza D9/N7, Yangwang U8 | Fully Supported |

---

## 2. Enabling Developer Options & USB Debugging

To sideload APK packages (`.apk`) or inspect runtime logs (`logcat`), developer options and USB debugging must be enabled on the vehicle screen:

### Standard Method:
1. Turn on the vehicle or place the power switch in **ACC / ON** mode.
2. Open **Vehicle Settings** from the main home screen.
3. Navigate to **System** > **About System / Software Version**.
4. Locate the **Build Number / Version Number** field.
5. Tap the Build Number **7 consecutive times rapidly**.
6. A toast message will appear: *"You are now a developer!"*.
7. Return back one step; a new menu entry **Developer Options** will now appear.
8. Enter Developer Options and enable:
   - **USB Debugging**
   - **Install via USB** (if present)
   - **Stay Awake** (optional, prevents screen sleep during development)

### Alternative Engineering Codes (If Menu is Hidden):
On select regional DiLink firmwares where developer settings are factory hidden, open the phone dialer or settings search box and enter:
- `*#*#2846579#*#*` (Opens the ProjectMenu to configure USB Ports Information).
- Or search directly for "Developer Options" via the system keyboard settings search bar.

> ⚠️ **Safety Warning:** Do not alter CAN-bus parameters or vehicle critical safety flags from engineering menus. Only enable ADB debugging and authorized application sideloading.

---

## 3. Vosk Offline Arabic Acoustic Model Setup

The speech recognition engine (`STTEngine.kt`) relies on a lightweight, embedded Arabic acoustic model from **Vosk**:

### Model Download:
1. Download the official compact Arabic model:
   - **Name:** `vosk-model-small-ar-0.22`
   - **URL:** [https://alphacephei.com/vosk/models/vosk-model-small-ar-0.22.zip](https://alphacephei.com/vosk/models/vosk-model-small-ar-0.22.zip)
   - **Size:** Approximately 45 MB (extremely compact, ideal for DiLink vehicle memory).

### Placing the Model in Project Assets Prior to Build:
1. Extract the downloaded zip file.
2. Rename the extracted folder to `model-ar` (or copy its contents directly).
3. Place it under the Android assets path:
   ```text
   android/app/src/main/assets/model-ar/
   ├── am/
   ├── conf/
   │   ├── mfcc.conf
   │   └── model.conf
   ├── graph/
   │   ├── HCLG.fst
   │   ├── disambig_tid.int
   │   └── phones/
   └── ivector/
   ```
4. On first application launch on the vehicle screen, `STTEngine` automatically unpacks the model into internal app storage via `StorageService.unpack(context, "model-ar", "model")` and initializes offline speech recognition.

---

## 4. Application Installation Methods

### Method 1: Installation via USB Flash Drive - Fastest & Simplest
1. After building `app-release.apk` (or `app-debug.apk`):
2. Prepare a USB flash drive formatted as **FAT32** or **NTFS**.
3. Copy `app-release.apk` directly onto the root of the flash drive.
4. Plug the flash drive into the vehicle's front console **USB Data Port** (typically indicated by a white icon or the primary USB Type-C port, not charge-only ports).
5. Open the native **File Manager** app on the DiLink touchscreen.
6. Open the external USB drive and tap `app-release.apk`.
7. Accept installation from unknown sources if prompted, then tap **Install**.

---

### Method 2: Wireless Installation via ADB over Wi-Fi
Ideal for active development and continuous updates without handling flash drives:

1. Connect both the laptop and DiLink vehicle head unit to the same Wi-Fi network (e.g., via a smartphone personal hotspot).
2. Open vehicle Wi-Fi settings to identify the screen's IP address (e.g., `192.168.43.150`).
3. On your laptop, open a terminal (PowerShell / Terminal) and execute:
   ```bash
   # Connect to the vehicle head unit on default ADB port 5555
   adb connect 192.168.43.150:5555

   # Verify connection status
   adb devices
   ```
4. Once the vehicle appears as an authorized `device`, deploy the APK directly:
   ```bash
   # Install application, replacing existing build and preserving data
   adb install -r android/app/build/outputs/apk/release/app-release.apk
   ```
5. Grant audio recording permission programmatically to avoid in-drive UI permission dialogs:
   ```bash
   adb shell pm grant com.byd.voiceassistant android.permission.RECORD_AUDIO
   ```

---

### Method 3: Direct Installation via USB Cable (ADB over USB)
1. Connect laptop to the DiLink front data port using a data-capable USB cable (Type-A to Type-A or Type-C to Type-C).
2. Accept the USB Debugging authorization prompt on the DiLink display, checking "Always allow from this computer".
3. Run the installation command:
   ```bash
   adb install -r android/app/build/outputs/apk/release/app-release.apk
   ```

---

## 5. Audio Focus & Permissions

### 1. Audio Focus & Ducking:
- `CarControlBridge` and audio engines request transient audio focus with ducking:
  ```kotlin
  AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
  ```
- **Automatic Behavior:** When Push-to-Talk is triggered or when the assistant speaks an answer:
  - Vehicle music/radio automatically ducks (lowers volume) so the driver's voice is clearly captured.
  - The assistant speaks synthesized Arabic speech crisply through the front speakers.
  - Upon completion of speech, media volume smoothly ramps back to its previous volume level.

### 2. Vehicle Microphone Matrix:
- Requires `android.permission.RECORD_AUDIO`.
- On DiLink hardware, roof-mounted cabin microphones are routed directly through standard Android audio input sources (`MediaRecorder.AudioSource.MIC` or `VOICE_RECOGNITION`), utilizing built-in automotive noise suppression and acoustic echo cancellation.

---

## 6. BYD Rotating Screen Handling

BYD vehicles feature motorized rotatable touchscreens (Landscape and Portrait):

1. **Zero Activity Re-creation During Rotation:**
   Configured in `AndroidManifest.xml` with:
   ```xml
   android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize"
   ```
   This ensures that screen rotation:
   - **Does NOT recreate the Activity** or re-initialize Vosk STT models.
   - Preserves ongoing audio capture and in-flight TTS playback without interruption.
2. **Adaptive Layout:**
   - `activity_main.xml` utilizes `ConstraintLayout` with percentage guidelines and flexible constraints, ensuring conversation message cards and the microphone action button scale seamlessly on both widescreen landscape (15.6") and vertical portrait views.

---

## 7. Diagnostics & Runtime Troubleshooting

Monitor live NLU routing, speech processing, and CAN-bus bridge execution via ADB logs:

```bash
# Monitor all voice assistant subsystem logs
adb logcat -s BYD_CarControl BYD_STT BYD_TTS BYD_Assistant

# Or filter exclusively for executed vehicle control actions
adb logcat -s BYD_CarControl
```

### Common Issues & Troubleshooting:

| Issue | Probable Cause | Recommended Resolution |
| :--- | :--- | :--- |
| **Assistant does not listen or closes immediately** | Missing microphone runtime permission | Go to Settings > Apps > BYD Voice Assistant > Permissions > Microphone > Allow, or execute `adb shell pm grant com.byd.voiceassistant android.permission.RECORD_AUDIO`. |
| **Vosk engine fails to initialize** | Speech model missing from `assets/model-ar` | Verify `vosk-model-small-ar-0.22` files are present in `android/app/src/main/assets/model-ar/` before compilation as documented in Section 3. |
| **Car commands execute but no audio response is spoken** | System TTS engine lacks Arabic voice data | Check Android Text-to-Speech settings (Text-to-Speech Settings > Google Speech Recognition & Synthesis) and ensure the Arabic voice data pack is downloaded and active. |
| **General knowledge queries fail** | Head unit lacks internet connectivity | General knowledge (weather, news, Wikipedia) requires an active internet connection (vehicle 4G/5G SIM or Wi-Fi hotspot). Offline Car Controls (Branch A) and Chitchat (Branch C) work 100% offline. |
| **ADB over Wi-Fi connection fails** | Laptop and head unit on different networks or firewall blocks port 5555 | Verify both devices are connected to the exact same subnet/hotspot and test network reachability via ping before running `adb connect`. |
