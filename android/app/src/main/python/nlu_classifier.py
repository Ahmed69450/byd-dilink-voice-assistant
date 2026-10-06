"""
NLU Classifier & Arabic Text Normalizer for BYD DiLink Voice Assistant.

Provides:
- normalize_arabic(text: str) -> str
- classify_intent(text: str) -> dict
"""

import re
import math
from typing import Dict, Any, Optional, Tuple, List


# =====================================================================
# Arabic Text Normalization
# =====================================================================

# Tashkeel (diacritics) regex
TASHKEEL_REGEX = re.compile(r"[\u064B-\u065F\u0670\u0640]")

# Arabic punctuation & symbols
PUNCTUATION_REGEX = re.compile(
    r"[؟،؛٪«»!?,.:;\"'`~@#$%^&*()_+=/\\\[\]{}|<>ـ\n\r\t-]"
)

# Arabic-Indic to ASCII digits
INDIC_TO_ASCII = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Character standardization mapping
CHAR_MAPPINGS = {
    # Alef variants -> ا
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    # Taa Marbuta -> ه
    "ة": "ه",
    # Alif Maqsura -> ي
    "ى": "ي",
    # Persian/Urdu variants to Arabic
    "ك": "ك",
    "ک": "ك",
    "ي": "ي",
    "ی": "ي",
    "پ": "ب",
    "ڤ": "ف",
    "چ": "ج",
    "گ": "ك",
}


def normalize_arabic(text: str) -> str:
    """
    Normalizes Arabic text:
    1. Removes diacritics (tashkeel & tatweel).
    2. Converts Arabic-Indic numerals to ASCII digits.
    3. Normalizes Alef variants (أ, إ, آ, ٱ -> ا).
    4. Normalizes Taa Marbuta (ة -> ه).
    5. Normalizes Alif Maqsura (ى -> ي).
    6. Strips punctuation and symbols.
    7. Trims and collapses multiple spaces.
    """
    if not text:
        return ""

    # Convert Indic digits to standard ASCII digits
    text = text.translate(INDIC_TO_ASCII)

    # Remove tashkeel (diacritics) & tatweel
    text = TASHKEEL_REGEX.sub("", text)

    # Character normalization
    chars = [CHAR_MAPPINGS.get(ch, ch) for ch in text]
    text = "".join(chars)

    # Strip punctuation and special symbols
    text = PUNCTUATION_REGEX.sub(" ", text)

    # Collapse multiple whitespaces and strip
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =====================================================================
# Numeric Entity Extraction (Digits & Arabic Words)
# =====================================================================

ARABIC_WORDS_RAW = {
    "صفر": 0,
    "واحد": 1,
    "اثنين": 2,
    "اثنان": 2,
    "ثلاثة": 3,
    "ثلاث": 3,
    "تلاتة": 3,
    "تلات": 3,
    "اربعة": 4,
    "اربع": 4,
    "خمسة": 5,
    "خمس": 5,
    "ستة": 6,
    "ست": 6,
    "سبعة": 7,
    "سبع": 7,
    "ثمانية": 8,
    "ثمان": 8,
    "تمانية": 8,
    "تمان": 8,
    "تسعة": 9,
    "تسع": 9,
    "عشرة": 10,
    "عشر": 10,
    "احد عشر": 11,
    "اثنا عشر": 12,
    "اثني عشر": 12,
    "ثلاثة عشر": 13,
    "اربعة عشر": 14,
    "خمسة عشر": 15,
    "ستة عشر": 16,
    "سبعة عشر": 17,
    "ثمانية عشر": 18,
    "تسعة عشر": 19,
    "عشرين": 20,
    "عشرون": 20,
    "ثلاثين": 30,
    "ثلاثون": 30,
    "تلاتين": 30,
    "اربعين": 40,
    "اربعون": 40,
    "خمسين": 50,
    "خمسون": 50,
    "ستين": 60,
    "ستون": 60,
    "سبعين": 70,
    "سبعون": 70,
    "ثمانين": 80,
    "ثمانون": 80,
    "تمانين": 80,
    "تسعين": 90,
    "تسعون": 90,
    "مئة": 100,
    "مية": 100,
    "ميه": 100,
}

ARABIC_WORDS_TO_NUM: Dict[str, int] = {}
for _k, _v in ARABIC_WORDS_RAW.items():
    ARABIC_WORDS_TO_NUM[_k] = _v
    ARABIC_WORDS_TO_NUM[normalize_arabic(_k)] = _v


def extract_numeric_value(text: str) -> Optional[int]:
    """
    Extracts a numeric value from text (digits or Arabic compound numbers).
    """
    # 1. Check for ASCII digits
    digit_match = re.search(r"\b(\d+)\b", text)
    if digit_match:
        try:
            return int(digit_match.group(1))
        except ValueError:
            pass

    # 2. Check for Arabic compound numbers like "اثنين وعشرين" or "خمسة وعشرين"
    norm = normalize_arabic(text)
    # Check compound (units + "و" + tens)
    compound_match = re.search(
        r"\b(واحد|اثنين|اثنان|ثلاثه|ثلاث|تلاته|تلات|اربعه|اربع|خمسه|خمس|سته|ست|سبعه|سبع|ثمانيه|ثمان|تمانيه|تمان|تسعه|تسع)\s+و\s*(عشرين|عشرون|ثلاثين|ثلاثون|تلاتين|اربعين|اربعون|خمسين|خمسون|ستين|ستون|سبعين|سبعون|ثمانين|ثمانون|تمانين|تسعين|تسعون)\b",
        norm,
    )
    if compound_match:
        unit_word = compound_match.group(1)
        tens_word = compound_match.group(2)
        unit_val = ARABIC_WORDS_TO_NUM.get(unit_word, 0)
        tens_val = ARABIC_WORDS_TO_NUM.get(tens_word, 0)
        if unit_val and tens_val:
            return unit_val + tens_val

    # Check standalone words
    for word, val in sorted(ARABIC_WORDS_TO_NUM.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(word)}\b", norm):
            return val

    return None


# =====================================================================
# Keyword & Pattern Dictionaries for Car Control
# =====================================================================

CAR_TARGETS = {
    "sunroof": [
        "فتحه السقف",
        "فتحه سقف",
        "بانوراما",
        "البانوراما",
        "سقف بانوراما",
        "ستاره السقف",
        "ستارة السقف",
        "فتحه السطح",
    ],
    "window": [
        "شباك",
        "شبابيك",
        "الشباك",
        "الشبابيك",
        "نافذه",
        "نافذة",
        "نوافذ",
        "النافذه",
        "النوافذ",
        "دريشه",
        "دريشة",
        "درايش",
        "الدريشه",
        "الدرايش",
        "جامه",
        "جامة",
        "جامات",
        "الجامه",
        "الجامات",
        "قزاز",
        "القزاز",
        "زجاج",
        "الزجاج",
    ],
    "ac": [
        "مكيف",
        "المكيف",
        "تكييف",
        "التكييف",
        "كوندشن",
        "الكوندشن",
        "اي سي",
        "تبريد",
        "التبريد",
        "تدفئه",
        "تدفئة",
        "التدفئه",
        "دفا",
        "حراره",
        "حرارة",
        "الحراره",
        "كمبروسر",
        "مروحه",
        "مروحة",
        "برد الجو",
        "برد السياره",
        "برد المقصوره",
        "دفي الجو",
        "دفي السياره",
        "دفئ الجو",
        "دفئ السياره",
        "دفئ",
        "سخن السياره",
        "سقع",
        "سخن الجو",
        "شوب",
    ],
    "light": [
        "نور",
        "النور",
        "انوار",
        "الانوار",
        "اضاءه",
        "اضاءة",
        "الاضاءه",
        "ليت",
        "ليتات",
        "الليتات",
        "الليت",
        "مصباح",
        "المصباح",
        "مصابيح",
        "المصابيح",
        "كشاف",
        "كشافات",
        "الكشافات",
        "فلاش",
    ],
    "volume": [
        "صوت",
        "الصوت",
        "مستوى الصوت",
        "حس الصوت",
        "حس",
        "ميوت",
        "كتم الصوت",
        "mute",
    ],
    "media": [
        "اغاني",
        "اغنيه",
        "اغنية",
        "الاغاني",
        "الاغنية",
        "موسيقى",
        "الموسيقى",
        "ميوزك",
        "راديو",
        "الراديو",
        "مسجل",
        "المسجل",
        "قران",
        "قرآن",
        "سوره",
        "سورة",
        "بودكاست",
        "مقطع",
        "تراك",
        "بلاي ليست",
        "محطه",
    ],
    "navigation": [
        "ملاحه",
        "ملاحة",
        "الملاحه",
        "خريطه",
        "خريطة",
        "الخريطه",
        "خرائط",
        "الخرائط",
        "نافيجيشن",
        "النافيجيشن",
        "جي بي اس",
        "gps",
        "navigation",
        "مسار",
        "وجهه",
        "وجهة",
        "طريق",
        "الطريق",
        "وديني",
        "خذني الي",
        "خذني الى",
        "دلني علي",
        "دلني على",
        "كيف اروح",
        "وجهني",
    ],
    "app": [
        "تطبيق",
        "تطبيقات",
        "التطبيق",
        "التطبيقات",
        "كاميرا",
        "كاميرات",
        "الكاميرا",
        "الكاميرات",
        "كاميرا 360",
        "كاميرات 360",
        "كاميره",
        "شاشه الطاقه",
        "شاشة الطاقة",
        "الطاقه",
        "اعدادات",
        "الإعدادات",
        "الاعدادات",
        "الضبط",
        "بلوتوث",
        "البلوتوث",
        "متصفح",
        "المتصفح",
        "ضغط الاطارات",
        "سجل الرحلات",
    ],
}

CAR_ACTIONS = {
    "turn_on": [
        "شغل",
        "تشغيل",
        "ولع",
        "توليع",
        "فعل",
        "تفعيل",
        "بدا",
        "start",
        "on",
    ],
    "turn_off": [
        "طفي",
        "اطفي",
        "اطفئ",
        "اطفاء",
        "بند",
        "وقف",
        "اوقف",
        "ايقاف",
        "توقيف",
        "كتم",
        "ميوت",
        "mute",
        "off",
        "stop",
    ],
    "open": [
        "افتح",
        "فتح",
        "فك",
        "نزل",
        "هبط",
    ],
    "close": [
        "سكر",
        "صك",
        "قفل",
        "اغلق",
        "غلق",
        "ارفع",
    ],
    "increase": [
        "علي",
        "اعلي",
        "رفع",
        "ارفع",
        "زود",
        "زيد",
        "كبر",
        "سرع",
        "دفي",
        "دفئ",
        "سخن",
    ],
    "decrease": [
        "وطي",
        "قصر",
        "خفض",
        "اخفض",
        "نقص",
        "قلل",
        "هدي",
        "رخي",
        "نزل",
        "برد",
    ],
    "set": [
        "اضبط",
        "ضبط",
        "حط",
        "خلي",
        "اجعل",
        "سوا",
        "عيير",
        "set",
    ],
}


# =====================================================================
# Chitchat & General Knowledge Patterns
# =====================================================================

CHITCHAT_PATTERNS = [
    r"\b(مرحبا|مرحباً|اهلا|اهلاً|اهلين|صباح الخير|مساء الخير|السلام عليكم|هلا|هاي|الو)\b",
    r"\b(كيف حالك|كيفك|شلونك|شخبارك|عساك بخير|ازيك|شو اخبارك|كيف الصحه|كيف امورك)\b",
    r"\b(من انت|مين انت|ما اسمك|شو اسمك|عرفني بنفسك|من تكون|مين صنعك|مين برمجك|مين طورك)\b",
    r"\b(شكرا|شكراً|مشكور|تسلم|يعطيك العافيه|ما قصرت|عشت|كفو|الف شكر)\b",
    r"\b(مع السلامه|مع السلامة|باي|وداعا|وداعاً|الي اللقاء|اشوفك علي خير|تصبح علي خير)\b",
    r"\b(نكته|نكتة|قل لي نكته|احكي لي نكته|ضحكني|سولف معي|احكي قصه)\b",
    r"\b(طفشان|زهقان|ملل|تعبان|حزين|فرحان|بردان|حران|احبك|انت ذكي|انت رائع|انت رهيب)\b",
]

GK_PATTERNS = [
    r"\b(كم المسافه|كم المسافة|كم بعد|المسافه بين|المسافة بين)\b",
    r"\b(ما هو الطقس|ما الطقس|كيف الجو|حاله الطقس|درجه الحراره في|درجة الحرارة في|هل ستمطر|توقعات الطقس)\b",
    r"\b(كم الساعه|كم الساعة|كم الوقت|الوقت في|الساعه في|الساعة في|تاريخ اليوم|كم التاريخ)\b",
    r"\b(ما هي عاصمه|ما هي عاصمة|عاصمه|عاصمة|ما اكبر|ما اصغر|كم عدد سكان|كم نسمه)\b",
    r"\b(من هو مخترع|من هو مؤسس|من اخترع|من اسس|من بنى|من كتب|من هو|من هي)\b",
    r"\b(احسب|ما ناتج|كم حاصل|زائد|ناقص|ضرب|تقسيم)\b",
    r"\b(اخر الاخبار|آخر الأخبار|اخبار اليوم|عناوين الاخبار|حدث اليوم)\b",
    r"\b(ما هو تعريف|ما معنى|ما المقصود ب|اين تقع|اين يقع|ما هي مميزات|ما سرعه|ما وزن)\b",
]


# =====================================================================
# Lightweight Pure-Python TF-IDF Engine
# =====================================================================

# Training corpus for intent scoring
TRAINING_DATA: List[Tuple[str, str]] = [
    # Car Control
    ("شغل التكييف على درجه 22", "car_control"),
    ("شغل المكيف", "car_control"),
    ("طفي المكيف", "car_control"),
    ("برد الجو شوي", "car_control"),
    ("دفي السياره", "car_control"),
    ("اضبط المكيف علي 20", "car_control"),
    ("نزل الجامه", "car_control"),
    ("سكر الشباك", "car_control"),
    ("افتح الدريشه", "car_control"),
    ("ارفع القزاز", "car_control"),
    ("افتح فتحه السقف", "car_control"),
    ("سكر البانوراما", "car_control"),
    ("شغل النور", "car_control"),
    ("طفي الليتات", "car_control"),
    ("علي الصوت", "car_control"),
    ("وطي الصوت", "car_control"),
    ("قصر علي الصوت", "car_control"),
    ("كتم الصوت", "car_control"),
    ("شغل الراديو", "car_control"),
    ("وقف الموسيقي", "car_control"),
    ("شغل اغنيه", "car_control"),
    ("وديني علي المطار", "car_control"),
    ("افتح الخريطه", "car_control"),
    ("افتح كاميرا 360", "car_control"),
    ("افتح تطبيق الطاقه", "car_control"),
    ("قفل الابواب", "car_control"),
    ("افتح الشنطه", "car_control"),
    ("خليه ابرد", "car_control"),
    ("خليه ادفي", "car_control"),
    ("سرع مروحه التكييف", "car_control"),
    ("اطفي انوار السياره", "car_control"),
    ("انوار السياره الداخليه", "car_control"),
    ("شغل القران", "car_control"),
    ("شغل سوره البقره", "car_control"),
    ("شاشه الطاقه والكاميرات", "car_control"),
    ("وجهني الي اقرب محطه وقود", "car_control"),
    ("كم باقي بنزين في السياره", "car_control"),
    ("حاله ضغط الاطارات", "car_control"),

    # Chitchat
    ("مرحبا يا مساعد", "chitchat"),
    ("صباح الخير", "chitchat"),
    ("مساء الخير", "chitchat"),
    ("السلام عليكم ورحمه الله", "chitchat"),
    ("كيف حالك اليوم", "chitchat"),
    ("شلونك شو اخبارك", "chitchat"),
    ("ازيك يا جميل", "chitchat"),
    ("من انت وماذا تفعل", "chitchat"),
    ("مين انت يا مساعد", "chitchat"),
    ("ما اسمك", "chitchat"),
    ("عرفني بنفسك", "chitchat"),
    ("شكرا جزيلا لك", "chitchat"),
    ("تسلم يعطيك العافيه", "chitchat"),
    ("مشكور ما قصرت", "chitchat"),
    ("مع السلامه اشوفك بخير", "chitchat"),
    ("باي وداعا", "chitchat"),
    ("قل لي نكته مضحكه", "chitchat"),
    ("احكي لي قصه", "chitchat"),
    ("انا طفشان وسولف معي", "chitchat"),
    ("انت ذكي جدا وشاطر", "chitchat"),
    ("احبك يا مساعد", "chitchat"),
    ("تصبح علي خير", "chitchat"),
    ("اهلا وسهلا", "chitchat"),
    ("هل انت انسان ام روبوت", "chitchat"),
    ("كم عمرك", "chitchat"),

    # General Knowledge
    ("كم المسافه بين الارض والقمر", "general_knowledge"),
    ("ما هو الطقس في الرياض", "general_knowledge"),
    ("كيف الجو في دبي غدا", "general_knowledge"),
    ("درجه الحراره في لندن الان", "general_knowledge"),
    ("هل ستمطر غدا في القاهره", "general_knowledge"),
    ("كم الساعه في طوكيو", "general_knowledge"),
    ("كم الوقت في نيويورك", "general_knowledge"),
    ("ما هو تاريخ اليوم", "general_knowledge"),
    ("ما هي عاصمه فرنسا", "general_knowledge"),
    ("من هو مخترع الكهرباء", "general_knowledge"),
    ("من هو مؤسس شركه ابل", "general_knowledge"),
    ("ما هو تعريف الذكاء الاصطناعي", "general_knowledge"),
    ("اين تقع اهرامات الجيزه", "general_knowledge"),
    ("كم عدد سكان مصر", "general_knowledge"),
    ("ما هي اكبر دوله في العالم", "general_knowledge"),
    ("احسب 25 زائد 30", "general_knowledge"),
    ("ما ناتج ضرب 15 في 4", "general_knowledge"),
    ("ما هي اخر الاخبار اليوم", "general_knowledge"),
    ("عناوين الاخبار العاجله", "general_knowledge"),
    ("ما سرعه الضوء في الفراغ", "general_knowledge"),
    ("من بني سور الصين العظيم", "general_knowledge"),
]


def _tokenize(text: str) -> List[str]:
    """Generates unigrams and bigrams from normalized Arabic text."""
    words = text.split()
    tokens = list(words)
    # Add bigrams
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    return tokens


class TfidfClassifier:
    """Lightweight pure-Python TF-IDF model."""

    def __init__(self, training_data: List[Tuple[str, str]]):
        self.classes = ["car_control", "chitchat", "general_knowledge"]
        self.doc_count = len(training_data)
        self.idf: Dict[str, float] = {}
        self.class_centroids: Dict[str, Dict[str, float]] = {c: {} for c in self.classes}
        self._train(training_data)

    def _train(self, training_data: List[Tuple[str, str]]):
        # Calculate document frequency
        df: Dict[str, int] = {}
        class_docs: Dict[str, List[List[str]]] = {c: [] for c in self.classes}

        for text, cls in training_data:
            norm_text = normalize_arabic(text)
            tokens = _tokenize(norm_text)
            class_docs[cls].append(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        # Calculate IDF: smooth IDF
        for token, count in df.items():
            self.idf[token] = math.log((self.doc_count + 1) / (count + 1)) + 1.0

        # Calculate class centroids (sum of TF-IDF vectors for each class, then normalized)
        for cls, docs in class_docs.items():
            centroid: Dict[str, float] = {}
            for tokens in docs:
                tf: Dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                for t, count in tf.items():
                    tfidf = (1.0 + math.log(count)) * self.idf.get(t, 1.0)
                    centroid[t] = centroid.get(t, 0.0) + tfidf

            # Normalize centroid vector
            norm = math.sqrt(sum(v * v for v in centroid.values()))
            if norm > 0:
                self.class_centroids[cls] = {k: v / norm for k, v in centroid.items()}

    def predict(self, text: str) -> Tuple[str, float]:
        norm_text = normalize_arabic(text)
        tokens = _tokenize(norm_text)
        if not tokens:
            return "chitchat", 0.3

        # Compute TF-IDF for input
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        vec: Dict[str, float] = {}
        for t, count in tf.items():
            if t in self.idf:
                vec[t] = (1.0 + math.log(count)) * self.idf[t]

        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm == 0:
            return "chitchat", 0.3

        normalized_vec = {k: v / norm for k, v in vec.items()}

        # Cosine similarity with each class centroid
        best_cls = "chitchat"
        best_sim = -1.0

        for cls in self.classes:
            centroid = self.class_centroids[cls]
            sim = sum(normalized_vec[k] * centroid[k] for k in normalized_vec if k in centroid)
            if sim > best_sim:
                best_sim = sim
                best_cls = cls

        return best_cls, max(0.0, min(1.0, best_sim))


# Initialize singleton TF-IDF model
_TFIDF_MODEL = TfidfClassifier(TRAINING_DATA)


# =====================================================================
# Entity Extraction for Car Control & General Knowledge
# =====================================================================

def _is_ali_increase(norm_text: str) -> bool:
    """
    Checks if 'علي' in norm_text functions as the verb 'علّي' (increase/raise),
    rather than the preposition 'على' (which normalizes to 'علي').
    Preposition indicators (does NOT trigger 'increase'):
    - Preceded by a set or control verb ('اضبط', 'ضبط', 'حط', 'خلي', 'اجعل', etc.)
    - Followed by a number (digit, Arabic number word, or prefix like 'درجه'/'مستوي' followed by number)
    """
    SET_OR_CONTROL_VERBS = {
        "اضبط", "ضبط", "حط", "خلي", "اجعل", "سوا", "عيير",
        "وطي", "قصر", "خفض", "اخفض", "نقص", "نزل", "رخي",
    }
    words = norm_text.split()
    for idx, w in enumerate(words):
        if w == "علي":
            # 1. Preceded by a set or control verb anywhere earlier in the sentence
            if any(prev in SET_OR_CONTROL_VERBS for prev in words[:idx]):
                continue
            # 2. Followed by a number
            if idx + 1 < len(words):
                next_word = words[idx + 1]
                if next_word.isdigit() or next_word in ARABIC_WORDS_TO_NUM:
                    continue
                if next_word in ["درجه", "درجة", "مستوي", "مستوى", "رقم", "حد"] and idx + 2 < len(words):
                    after_next = words[idx + 2]
                    if after_next.isdigit() or after_next in ARABIC_WORDS_TO_NUM:
                        continue
            return True
    return False


def _extract_car_entities(raw_text: str, norm_text: str) -> Dict[str, Any]:
    """
    Extracts car_control entities:
    - target: ac, window, sunroof, light, media, volume, navigation, app
    - action: turn_on, turn_off, open, close, increase, decrease, set
    - value: numeric value (temperature or volume)
    - raw_text: original input
    """
    entities: Dict[str, Any] = {"raw_text": raw_text}

    # 1. Target Detection
    detected_target: Optional[str] = None

    # Check sunroof before window
    for kw in CAR_TARGETS["sunroof"]:
        norm_kw = normalize_arabic(kw)
        if norm_kw in norm_text:
            detected_target = "sunroof"
            break

    if not detected_target:
        # Check specific order: volume, navigation, app, light, media, window, ac
        order = ["volume", "navigation", "app", "light", "media", "window", "ac"]
        for target in order:
            for kw in CAR_TARGETS[target]:
                norm_kw = normalize_arabic(kw)
                # Word boundary or exact phrase match
                if re.search(rf"(?:^|\s){re.escape(norm_kw)}(?:\s|$)", norm_text):
                    detected_target = target
                    break
            if detected_target:
                break

    # Contextual target inference from verbs if target not explicitly mentioned
    if not detected_target:
        if any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["برد الجو", "برد السياره", "برد", "دفي الجو", "دفي السياره", "دفي", "دفئ الجو", "دفئ السياره", "دفئ", "سخن الجو", "سخن"]):
            detected_target = "ac"
        elif any(w in norm_text for w in ["نزل الجامه", "نزل الشباك", "ارفع الجامه", "ارفع الشباك", "ارفع القزاز", "نزل القزاز"]):
            detected_target = "window"
        elif "وديني" in norm_text or "خذني" in norm_text or "دلني" in norm_text:
            detected_target = "navigation"

    if detected_target:
        entities["target"] = detected_target

    # 2. Action Detection
    detected_action: Optional[str] = None

    # Special verb-target combinations
    if detected_target == "window":
        if any(w in norm_text for w in ["نزل", "افتح", "فك"]):
            detected_action = "open"
        elif any(w in norm_text for w in ["ارفع", "سكر", "قفل", "صك", "اغلق"]):
            detected_action = "close"
    elif detected_target == "sunroof":
        if any(w in norm_text for w in ["افتح", "فك"]):
            detected_action = "open"
        elif any(w in norm_text for w in ["سكر", "قفل", "صك", "اغلق"]):
            detected_action = "close"
    elif detected_target == "volume":
        if any(w in norm_text for w in ["كتم", "ميوت", "طفي", "وقف", "صامت"]):
            detected_action = "turn_off"
        elif any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["اضبط", "ضبط", "حط", "خلي", "اجعل"]):
            detected_action = "set"
        elif any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["وطي", "قصر", "خفض", "اخفض", "نقص", "نزل", "رخي"]):
            detected_action = "decrease"
        elif any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["اعلي", "ارفع", "زود", "زيد", "كبر"]) or _is_ali_increase(norm_text):
            detected_action = "increase"
    elif detected_target == "ac":
        if any(w in norm_text for w in ["طفي", "اطفي", "اطفئ", "بند"]):
            detected_action = "turn_off"
        elif any(w in norm_text for w in ["شغل", "تشغيل", "ولع"]):
            detected_action = "turn_on"
        elif any(w in norm_text for w in ["اضبط", "ضبط", "حط", "خلي", "اجعل"]):
            detected_action = "set"
        elif any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["برد", "سقع", "وطي", "خفض", "اخفض", "نقص", "نزل"]):
            detected_action = "decrease"
        elif any(w in norm_text for w in ["دفي", "دفئ", "سخن", "اعلي", "ارفع", "زود"]):
            detected_action = "increase"

    # General action matching if not yet determined
    if not detected_action:
        # Check turn_on / turn_off
        for act in ["turn_off", "turn_on", "set", "increase", "decrease", "open", "close"]:
            for kw in CAR_ACTIONS[act]:
                norm_kw = normalize_arabic(kw)
                if norm_kw == "علي" and not _is_ali_increase(norm_text):
                    continue
                if re.search(rf"(?:^|\s){re.escape(norm_kw)}(?:\s|$)", norm_text):
                    # Adjust 'open'/'close' for electronic devices
                    if detected_target in ["light", "media", "ac"] and act == "open":
                        detected_action = "turn_on"
                    elif detected_target in ["light", "media", "ac"] and act == "close":
                        detected_action = "turn_off"
                    else:
                        detected_action = act
                    break
            if detected_action:
                break

    if detected_action:
        entities["action"] = detected_action

    # 3. Value Extraction (temperature / volume level)
    val = extract_numeric_value(norm_text)
    if val is not None:
        entities["value"] = val

    return entities


def _extract_location_entity(norm_text: str) -> Optional[str]:
    """Extracts mentioned city/location from query if present (e.g. 'في الرياض')."""
    match = re.search(r"\bفي\s+([^\s?]+(?:\s+[^\s?]+)?)", norm_text)
    if match:
        loc = match.group(1).strip()
        # Avoid non-location words
        if loc not in ["السياره", "السيارة", "البيت", "طريق", "العالم"]:
            return loc
    return None


# =====================================================================
# Main Classification Function
# =====================================================================

def classify_intent(text: str) -> Dict[str, Any]:
    """
    Classifies the user input text into one of three intents:
    - 'car_control'
    - 'chitchat'
    - 'general_knowledge'

    Returns:
    {
        "intent": str,
        "confidence": float,
        "entities": dict
    }
    """
    if not text or not text.strip():
        return {
            "intent": "chitchat",
            "confidence": 0.0,
            "entities": {"raw_text": text or ""},
        }

    norm_text = normalize_arabic(text)

    # -----------------------------------------------------------------
    # 1. Rule / Pattern Matching
    # -----------------------------------------------------------------

    # Check Car Control rules
    car_entities = _extract_car_entities(text, norm_text)
    has_car_target = "target" in car_entities
    has_car_action = "action" in car_entities

    # Disambiguation: "درجة الحرارة في <مكان>" is General Knowledge, NOT car control!
    is_weather_query = bool(re.search(r"\b(درجه الحراره في|الطقس في|الجو في|كيف الجو)\b", norm_text))

    # Car control match
    is_car_control_rule = False
    if not is_weather_query:
        if has_car_target and has_car_action:
            is_car_control_rule = True
        elif has_car_target and ("value" in car_entities or car_entities.get("target") in ["navigation", "app"]):
            is_car_control_rule = True
        elif has_car_target and any(re.search(rf"(?:^|\s){re.escape(w)}(?:\s|$)", norm_text) for w in ["برد", "دفي", "دفئ", "سخن", "شوي", "خليه"]):
            is_car_control_rule = True
        elif any(phrase in norm_text for phrase in [
            "نزل الجامه", "سكر الشباك", "افتح الدريشه", "ارفع القزاز", "افتح فتحه السقف",
            "سكر البانوراما", "علي الصوت", "وطي الصوت", "قصر علي الصوت", "كتم الصوت",
            "طفي المكيف", "شغل المكيف", "برد الجو", "دفي السياره", "دفئ السياره", "دفئ الجو", "وديني", "افتح كاميرا 360"
        ]):
            is_car_control_rule = True

    # Check Chitchat patterns
    is_chitchat_rule = False
    for pat in CHITCHAT_PATTERNS:
        if re.search(pat, norm_text):
            is_chitchat_rule = True
            break

    # Check General Knowledge patterns
    is_gk_rule = False
    for pat in GK_PATTERNS:
        if re.search(pat, norm_text):
            is_gk_rule = True
            break

    # -----------------------------------------------------------------
    # 2. Decision Logic & TF-IDF Fallback
    # -----------------------------------------------------------------

    tfidf_intent, tfidf_conf = _TFIDF_MODEL.predict(norm_text)

    # Priority 1: Clear Car Control
    if is_car_control_rule:
        intent = "car_control"
        confidence = 0.95 if (has_car_target and has_car_action) else 0.88
        entities = car_entities
        return {
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities,
        }

    # Priority 2: Clear General Knowledge (factual/math/weather/time/distance)
    if is_gk_rule:
        intent = "general_knowledge"
        confidence = 0.94
        entities = {"raw_text": text}
        loc = _extract_location_entity(norm_text)
        if loc:
            entities["location"] = loc
        return {
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities,
        }

    # Priority 3: Clear Chitchat
    if is_chitchat_rule:
        intent = "chitchat"
        confidence = 0.92
        entities = {"raw_text": text}
        return {
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities,
        }

    # Priority 4: If target detected without explicit action but car-related
    if has_car_target and not is_weather_query:
        intent = "car_control"
        confidence = 0.80
        entities = car_entities
        return {
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities,
        }

    # Priority 5: Fallback to TF-IDF classifier
    intent = tfidf_intent
    confidence = max(0.60, round(float(tfidf_conf), 2))
    entities = car_entities if intent == "car_control" else {"raw_text": text}
    if intent == "general_knowledge":
        loc = _extract_location_entity(norm_text)
        if loc:
            entities["location"] = loc

    return {
        "intent": intent,
        "confidence": float(confidence),
        "entities": entities,
    }
