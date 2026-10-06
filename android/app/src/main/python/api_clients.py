"""
REST API Clients for Branch B (General Knowledge, Weather, News, Time, and Calculations)
for the BYD DiLink Voice Assistant.

Provides:
- query_weather & format_weather_response (Open-Meteo API)
- query_time & format_time_response (WorldTimeAPI)
- query_news (NewsAPI)
- query_duckduckgo (DuckDuckGo Instant Answer API)
- query_wolfram (Wolfram Alpha Short Answers API)
- handle_general_knowledge (Branch B Master Dispatcher)

Guarantees:
- 100% crash-proof: catches all network, parsing, and timeout exceptions.
- Hard 5.0s maximum timeout on all external calls.
- Natural spoken Arabic responses.
- Graceful offline fallback with friendly Arabic guidance.
"""

import os
import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


# Canonical offline fallback message
OFFLINE_FALLBACK_MESSAGE = (
    "لا يتوفر اتصال بالإنترنت حالياً للبحث عن هذه المعلومة، ولكن يمكنك استخدام أوامر السيارة أو التحدث معي."
)

# Network call timeout constraint (max 5.0 seconds)
DEFAULT_TIMEOUT_SECONDS = 5.0


# =====================================================================
# WMO Weather Codes & Interpretation (Open-Meteo)
# =====================================================================

WMO_WEATHER_CODES = {
    0: "صافٍ",
    1: "صحو بوجه عام",
    2: "غائم جزئياً",
    3: "غائم",
    45: "ضبابي",
    48: "ضباب متجمد",
    51: "رذاذ خفيف",
    53: "رذاذ معتدل",
    55: "رذاذ كثيف",
    56: "رذاذ متجمد خفيف",
    57: "رذاذ متجمد كثيف",
    61: "ممطر بأمطار خفيفة",
    63: "ممطر بأمطار معتدلة",
    65: "ممطر بأمطار غزيرة",
    66: "أمطار متجمدة خفيفة",
    67: "أمطار متجمدة غزيرة",
    71: "تساقط ثلوج خفيفة",
    73: "تساقط ثلوج معتدلة",
    75: "تساقط ثلوج كثيفة",
    77: "حبيبات ثلجية",
    80: "زخات مطر خفيفة",
    81: "زخات مطر معتدلة",
    82: "زخات مطر عنيفة",
    85: "زخات ثلوج خفيفة",
    86: "زخات ثلوج كثيفة",
    95: "عواصف رعدية",
    96: "عواصف رعدية مصحوبة ببَرَد خفيف",
    99: "عواصف رعدية مصحوبة ببَرَد كثيف",
}


# =====================================================================
# Arabic & International Cities Geocoding & Timezone Registry
# =====================================================================

ARABIC_CITIES: Dict[str, Dict[str, Any]] = {
    # Saudi Arabia
    "الرياض": {"lat": 24.7136, "lon": 46.6753, "timezone": "Asia/Riyadh"},
    "مكة": {"lat": 21.3891, "lon": 39.8579, "timezone": "Asia/Riyadh"},
    "مكة المكرمة": {"lat": 21.3891, "lon": 39.8579, "timezone": "Asia/Riyadh"},
    "المدينة": {"lat": 24.5247, "lon": 39.5692, "timezone": "Asia/Riyadh"},
    "المدينة المنورة": {"lat": 24.5247, "lon": 39.5692, "timezone": "Asia/Riyadh"},
    "جدة": {"lat": 21.5433, "lon": 39.1728, "timezone": "Asia/Riyadh"},
    "الدمام": {"lat": 26.4207, "lon": 50.0888, "timezone": "Asia/Riyadh"},
    "الخبر": {"lat": 26.2818, "lon": 50.2084, "timezone": "Asia/Riyadh"},
    "الطائف": {"lat": 21.4373, "lon": 40.5127, "timezone": "Asia/Riyadh"},
    "تبوك": {"lat": 28.3835, "lon": 36.5662, "timezone": "Asia/Riyadh"},
    "أبها": {"lat": 18.2164, "lon": 42.5053, "timezone": "Asia/Riyadh"},
    "ابها": {"lat": 18.2164, "lon": 42.5053, "timezone": "Asia/Riyadh"},
    "بريدة": {"lat": 26.3592, "lon": 43.9818, "timezone": "Asia/Riyadh"},
    "حائل": {"lat": 27.5114, "lon": 41.7208, "timezone": "Asia/Riyadh"},
    "جازان": {"lat": 16.8892, "lon": 42.5706, "timezone": "Asia/Riyadh"},
    "نجران": {"lat": 17.4924, "lon": 44.1277, "timezone": "Asia/Riyadh"},

    # United Arab Emirates
    "دبي": {"lat": 25.2048, "lon": 55.2708, "timezone": "Asia/Dubai"},
    "أبوظبي": {"lat": 24.4539, "lon": 54.3773, "timezone": "Asia/Dubai"},
    "ابوظبي": {"lat": 24.4539, "lon": 54.3773, "timezone": "Asia/Dubai"},
    "الشارقة": {"lat": 25.3573, "lon": 55.4033, "timezone": "Asia/Dubai"},
    "الشارقه": {"lat": 25.3573, "lon": 55.4033, "timezone": "Asia/Dubai"},
    "عجمان": {"lat": 25.4052, "lon": 55.5136, "timezone": "Asia/Dubai"},
    "رأس الخيمة": {"lat": 25.7895, "lon": 55.9432, "timezone": "Asia/Dubai"},
    "العين": {"lat": 24.1302, "lon": 55.8023, "timezone": "Asia/Dubai"},

    # GCC & Levant
    "الدوحة": {"lat": 25.2854, "lon": 51.5310, "timezone": "Asia/Qatar"},
    "الدوحه": {"lat": 25.2854, "lon": 51.5310, "timezone": "Asia/Qatar"},
    "الكويت": {"lat": 29.3759, "lon": 47.9774, "timezone": "Asia/Kuwait"},
    "مدينة الكويت": {"lat": 29.3759, "lon": 47.9774, "timezone": "Asia/Kuwait"},
    "المنامة": {"lat": 26.2285, "lon": 50.5860, "timezone": "Asia/Bahrain"},
    "المنامه": {"lat": 26.2285, "lon": 50.5860, "timezone": "Asia/Bahrain"},
    "مسقط": {"lat": 23.5880, "lon": 58.3829, "timezone": "Asia/Muscat"},
    "بغداد": {"lat": 33.3152, "lon": 44.3661, "timezone": "Asia/Baghdad"},
    "البصرة": {"lat": 30.5081, "lon": 47.7835, "timezone": "Asia/Baghdad"},
    "البصره": {"lat": 30.5081, "lon": 47.7835, "timezone": "Asia/Baghdad"},
    "أربيل": {"lat": 36.1911, "lon": 44.0092, "timezone": "Asia/Baghdad"},
    "اريل": {"lat": 36.1911, "lon": 44.0092, "timezone": "Asia/Baghdad"},
    "عمان": {"lat": 31.9454, "lon": 35.9284, "timezone": "Asia/Amman"},
    "بيروت": {"lat": 33.8938, "lon": 35.5018, "timezone": "Asia/Beirut"},
    "دمشق": {"lat": 33.5138, "lon": 36.2765, "timezone": "Asia/Damascus"},
    "حلب": {"lat": 36.2021, "lon": 37.1343, "timezone": "Asia/Damascus"},
    "القدس": {"lat": 31.7683, "lon": 35.2137, "timezone": "Asia/Jerusalem"},
    "غزة": {"lat": 31.5017, "lon": 34.4668, "timezone": "Asia/Gaza"},
    "صنعاء": {"lat": 15.3694, "lon": 44.1910, "timezone": "Asia/Riyadh"},
    "عدن": {"lat": 12.7855, "lon": 45.0187, "timezone": "Asia/Riyadh"},

    # North Africa
    "القاهرة": {"lat": 30.0444, "lon": 31.2357, "timezone": "Africa/Cairo"},
    "القاهره": {"lat": 30.0444, "lon": 31.2357, "timezone": "Africa/Cairo"},
    "الإسكندرية": {"lat": 31.2001, "lon": 29.9187, "timezone": "Africa/Cairo"},
    "الاسكندرية": {"lat": 31.2001, "lon": 29.9187, "timezone": "Africa/Cairo"},
    "الاسكندريه": {"lat": 31.2001, "lon": 29.9187, "timezone": "Africa/Cairo"},
    "طرابلس": {"lat": 32.8872, "lon": 13.1913, "timezone": "Africa/Tripoli"},
    "بنغازي": {"lat": 32.1167, "lon": 20.0667, "timezone": "Africa/Tripoli"},
    "تونس": {"lat": 36.8065, "lon": 10.1815, "timezone": "Africa/Tunis"},
    "الجزائر": {"lat": 36.7538, "lon": 3.0588, "timezone": "Africa/Algiers"},
    "الرباط": {"lat": 34.0209, "lon": -6.8416, "timezone": "Africa/Casablanca"},
    "الدار البيضاء": {"lat": 33.5731, "lon": -7.5898, "timezone": "Africa/Casablanca"},
    "كازابلانكا": {"lat": 33.5731, "lon": -7.5898, "timezone": "Africa/Casablanca"},
    "مراكش": {"lat": 31.6295, "lon": -7.9811, "timezone": "Africa/Casablanca"},
    "الخرطوم": {"lat": 15.5007, "lon": 32.5599, "timezone": "Africa/Khartoum"},

    # Major International Cities
    "لندن": {"lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"},
    "باريس": {"lat": 48.8566, "lon": 2.3522, "timezone": "Europe/Paris"},
    "نيويورك": {"lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    "واشنطن": {"lat": 38.9072, "lon": -77.0369, "timezone": "America/New_York"},
    "طوكيو": {"lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
    "إسطنبول": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
    "اسطنبول": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
    "برلين": {"lat": 52.5200, "lon": 13.4050, "timezone": "Europe/Berlin"},
    "روما": {"lat": 41.9028, "lon": 12.4964, "timezone": "Europe/Rome"},
    "مدريد": {"lat": 40.4168, "lon": -3.7038, "timezone": "Europe/Madrid"},
    "موسكو": {"lat": 55.7558, "lon": 37.6173, "timezone": "Europe/Moscow"},
    "بكين": {"lat": 39.9042, "lon": 116.4074, "timezone": "Asia/Shanghai"},
}


# =====================================================================
# Internal Network Requester Helper
# =====================================================================

def _http_get_json(url: str, params: Optional[dict] = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Tuple[int, Any]:
    """
    Safely executes an HTTP GET request and returns (status_code, json_or_dict).
    Uses `requests` if available, falls back to `urllib.request`.
    Respects maximum 5.0 second timeout.
    """
    timeout = min(float(timeout), DEFAULT_TIMEOUT_SECONDS)
    full_url = url
    if params:
        qs = urllib.parse.urlencode(params)
        full_url = f"{url}?{qs}" if "?" not in url else f"{url}&{qs}"

    if HAS_REQUESTS:
        # Standard requests library call (mockable via unittest.mock.patch('requests.get'))
        resp = requests.get(full_url, timeout=timeout)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, {}
    else:
        # Fallback to urllib.request
        req = urllib.request.Request(full_url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            import json
            data = json.loads(response.read().decode("utf-8"))
            return response.status, data


def _http_get_text(url: str, params: Optional[dict] = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Tuple[int, str]:
    """
    Safely executes an HTTP GET request and returns (status_code, text).
    Uses `requests` if available, falls back to `urllib.request`.
    """
    timeout = min(float(timeout), DEFAULT_TIMEOUT_SECONDS)
    full_url = url
    if params:
        qs = urllib.parse.urlencode(params)
        full_url = f"{url}?{qs}" if "?" not in url else f"{url}&{qs}"

    if HAS_REQUESTS:
        resp = requests.get(full_url, timeout=timeout)
        return resp.status_code, resp.text
    else:
        req = urllib.request.Request(full_url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")


# =====================================================================
# Location & City Resolution Helper
# =====================================================================

def resolve_city_coordinates(location_name: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Dict[str, Any]]:
    """
    Resolves city name to coordinates {'lat': float, 'lon': float, 'timezone': str, 'name': str}.
    Checks pre-defined Arabic cities dictionary first.
    Falls back to Open-Meteo Geocoding API if unknown.
    """
    clean_name = location_name.strip()
    if clean_name in ARABIC_CITIES:
        data = ARABIC_CITIES[clean_name].copy()
        data["name"] = clean_name
        return data

    # Try simple character normalization for matching
    norm_name = clean_name.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    for city, data in ARABIC_CITIES.items():
        city_norm = city.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        if norm_name == city_norm:
            res = data.copy()
            res["name"] = city
            return res

    # Fallback to Open-Meteo Geocoding API
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": clean_name, "count": 1, "language": "ar"}
        status, json_data = _http_get_json(url, params=params, timeout=timeout)
        if status == 200 and json_data and "results" in json_data and json_data["results"]:
            first = json_data["results"][0]
            return {
                "lat": float(first.get("latitude")),
                "lon": float(first.get("longitude")),
                "timezone": first.get("timezone", "Asia/Riyadh"),
                "name": first.get("name", clean_name),
            }
    except Exception:
        pass

    return None


# =====================================================================
# 1. Weather Client (Open-Meteo)
# =====================================================================

def format_weather_response(location_name: str, weather_data: dict) -> str:
    """
    Formats Open-Meteo current_weather data into spoken Arabic:
    e.g. "درجة الحرارة في الرياض حالياً 28 درجة مئوية، والطقس صافٍ، وسرعة الرياح 12 كم/ساعة."
    """
    current = weather_data.get("current_weather", weather_data)
    temp = current.get("temperature", 0)
    code = current.get("weathercode", current.get("weather_code", 0))
    wind = current.get("windspeed", current.get("wind_speed", 0))

    if isinstance(temp, (int, float)):
        if float(temp).is_integer():
            temp_str = str(int(temp))
        else:
            temp_str = f"{temp:.1f}".rstrip("0").rstrip(".")
    else:
        temp_str = str(temp)

    if isinstance(wind, (int, float)):
        if float(wind).is_integer():
            wind_str = str(int(wind))
        else:
            wind_str = f"{wind:.1f}".rstrip("0").rstrip(".")
    else:
        wind_str = str(wind)

    condition = WMO_WEATHER_CODES.get(int(code), "معتدل")
    return (
        f"درجة الحرارة في {location_name} حالياً {temp_str} درجة مئوية، "
        f"والطقس {condition}، وسرعة الرياح {wind_str} كم/ساعة."
    )


def query_weather(
    location_name: str = "الرياض",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """
    Queries Open-Meteo Weather API for current weather at the specified location.
    Translates popular Arabic cities to coordinates or uses Open-Meteo geocoding.
    Returns natural spoken Arabic forecast or graceful offline message.
    """
    loc_name = city or location_name or "الرياض"

    try:
        if lat is None or lon is None:
            geo_info = resolve_city_coordinates(loc_name, timeout=timeout)
            if not geo_info:
                return f"لم أتمكن من العثور على موقع '{loc_name}' لمعرفة الطقس."
            lat = geo_info["lat"]
            lon = geo_info["lon"]
            loc_name = geo_info.get("name", loc_name)

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

        status, data = _http_get_json(url, timeout=timeout)
        if status == 200 and data:
            return format_weather_response(loc_name, data)
        else:
            return OFFLINE_FALLBACK_MESSAGE

    except Exception:
        return OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# 2. World Time Client (WorldTimeAPI)
# =====================================================================

ARABIC_HOURS_WORDS = {
    0: "الثانية عشرة",
    1: "الواحدة",
    2: "الثانية",
    3: "الثالثة",
    4: "الرابعة",
    5: "الخامسة",
    6: "السادسة",
    7: "السابعة",
    8: "الثامنة",
    9: "التاسعة",
    10: "العاشرة",
    11: "الحادية عشرة",
    12: "الثانية عشرة",
}


def format_time_response(location_name: str, iso_datetime_or_time_str: str) -> str:
    """
    Converts ISO datetime or HH:MM string to spoken Arabic:
    e.g. "الوقت الحالي في دبي هو الثانية والنصف مساءً (14:30)."
    """
    match = re.search(r"(\d{1,2}):(\d{2})", iso_datetime_or_time_str)
    if not match:
        return f"الوقت الحالي في {location_name} هو {iso_datetime_or_time_str}."

    hour = int(match.group(1))
    minute = int(match.group(2))

    h12 = hour % 12
    if h12 == 0:
        h12 = 12

    if hour < 12:
        period = "صباحاً"
    elif hour == 12:
        period = "ظهراً"
    else:
        period = "مساءً"

    if minute == 0:
        spoken = f"{ARABIC_HOURS_WORDS[h12]} {period}"
    elif minute == 15:
        spoken = f"{ARABIC_HOURS_WORDS[h12]} والربع {period}"
    elif minute == 20:
        spoken = f"{ARABIC_HOURS_WORDS[h12]} والثلث {period}"
    elif minute == 30:
        spoken = f"{ARABIC_HOURS_WORDS[h12]} والنصف {period}"
    elif minute == 40:
        next_h = (h12 % 12) + 1
        spoken = f"{ARABIC_HOURS_WORDS[next_h]} إلا ثلثاً {period}"
    elif minute == 45:
        next_h = (h12 % 12) + 1
        spoken = f"{ARABIC_HOURS_WORDS[next_h]} إلا ربعاً {period}"
    elif minute == 50:
        next_h = (h12 % 12) + 1
        spoken = f"{ARABIC_HOURS_WORDS[next_h]} إلا عشر دقائق {period}"
    elif minute == 55:
        next_h = (h12 % 12) + 1
        spoken = f"{ARABIC_HOURS_WORDS[next_h]} إلا خمس دقائق {period}"
    else:
        spoken = f"{ARABIC_HOURS_WORDS[h12]} و{minute} دقيقة {period}"

    return f"الوقت الحالي في {location_name} هو {spoken} ({hour:02d}:{minute:02d})."


def query_time(
    location_name: str = "الرياض",
    city_or_timezone: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """
    Queries WorldTimeAPI for the current time in the given city or timezone.
    Returns clear formatted Arabic spoken output or offline fallback.
    """
    loc_name = city_or_timezone or location_name or "الرياض"

    try:
        # Determine timezone string
        if "/" in loc_name:
            tz = loc_name
            display_name = loc_name.split("/")[-1].replace("_", " ")
        else:
            geo_info = resolve_city_coordinates(loc_name, timeout=timeout)
            tz = geo_info["timezone"] if geo_info else "Asia/Riyadh"
            display_name = loc_name

        url = f"http://worldtimeapi.org/api/timezone/{tz}"
        status, data = _http_get_json(url, timeout=timeout)

        if status == 200 and data and "datetime" in data:
            dt_str = data["datetime"]
            return format_time_response(display_name, dt_str)
        else:
            return OFFLINE_FALLBACK_MESSAGE

    except Exception:
        return OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# 3. NewsAPI Client
# =====================================================================

def query_news(
    topic: str = "",
    country: str = "sa",
    api_key: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """
    Queries NewsAPI top-headlines endpoint and formats the top 2-3 headlines in spoken Arabic.
    If no API key is provided, returns informative configuration guidance.
    """
    key = api_key or os.environ.get("NEWS_API_KEY", "")
    if not key:
        return "خدمة الأخبار تتطلب ضبط مفتاح NewsAPI، يرجى ضبط المفتاح في الإعدادات."

    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {"country": country, "apiKey": key}
        if topic:
            params["q"] = topic

        status, data = _http_get_json(url, params=params, timeout=timeout)
        if status == 200 and data and data.get("status") == "ok":
            articles = data.get("articles", [])
            valid_articles = [
                a for a in articles
                if a.get("title") and "[Removed]" not in a.get("title", "")
            ]

            if not valid_articles:
                return "لم يتم العثور على أخبار جديدة حالياً."

            ordinals = ["أولاً", "ثانياً", "ثالثاً"]
            items = []
            for i, article in enumerate(valid_articles[:3]):
                title = article.get("title", "").strip()
                items.append(f"{ordinals[i]}: {title}")

            return "إليك أبرز عناوين الأخبار: " + ". ".join(items) + "."
        else:
            return OFFLINE_FALLBACK_MESSAGE

    except Exception:
        return OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# 4. DuckDuckGo Instant Answer API
# =====================================================================

def query_duckduckgo(
    query: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    raise_errors: bool = False,
) -> Optional[str]:
    """
    Calls DuckDuckGo Instant Answer API (https://api.duckduckgo.com/).
    Extracts AbstractText, Answer, or first RelatedTopic text.
    Returns plain string or None if nothing found / offline.
    """
    clean_query = query.strip()
    if not clean_query:
        return None

    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_query)}&format=json&no_html=1&skip_disambig=1"
        status, data = _http_get_json(url, timeout=timeout)
        if status == 200 and isinstance(data, dict):
            # 1. AbstractText
            abstract = data.get("AbstractText", "").strip()
            if abstract:
                return abstract

            # 2. Answer
            answer = data.get("Answer", "").strip()
            if answer:
                return answer

            # 3. RelatedTopics
            related = data.get("RelatedTopics", [])
            if related and isinstance(related, list):
                first = related[0]
                if isinstance(first, dict):
                    text = first.get("Text", "").strip()
                    if text:
                        return text
                    # Subtopics
                    topics = first.get("Topics", [])
                    if topics and isinstance(topics, list) and isinstance(topics[0], dict):
                        sub_text = topics[0].get("Text", "").strip()
                        if sub_text:
                            return sub_text

        return None
    except Exception:
        if raise_errors:
            raise
        return None


# =====================================================================
# 5. Wolfram Alpha Short Answers API
# =====================================================================

def query_wolfram(
    query: str,
    app_id: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    raise_errors: bool = False,
) -> Optional[str]:
    """
    Calls Wolfram Alpha Short Answers API (http://api.wolframalpha.com/v1/result).
    Returns concise answer string or None if unavailable/offline.
    """
    key = app_id or os.environ.get("WOLFRAM_APP_ID", "")
    if not key:
        return None

    clean_query = query.strip()
    if not clean_query:
        return None

    try:
        url = f"http://api.wolframalpha.com/v1/result?appid={key}&i={urllib.parse.quote(clean_query)}"
        status, text = _http_get_text(url, timeout=timeout)
        if status == 200 and text and text.strip():
            return text.strip()
        return None
    except Exception:
        if raise_errors:
            raise
        return None


# =====================================================================
# Local Safe Arithmetic Evaluator (Offline Math Calculation)
# =====================================================================

def _safe_calculate_arabic_math(query: str) -> Optional[str]:
    """
    Parses and safely computes basic arithmetic queries in Arabic:
    e.g. "احسب 25 زائد 30", "ما ناتج ضرب 15 في 4", "100 تقسيم 4", "50 ناقص 20".
    """
    norm = query.replace("،", " ").replace("؟", " ").replace("!", " ")

    # Map Arabic arithmetic operators to standard symbols
    norm = re.sub(r"\b(زائد|جمع|مع)\b", "+", norm)
    norm = re.sub(r"\b(ناقص|طرح)\b", "-", norm)
    norm = re.sub(r"\b(ضرب|مضروب في|مضروبا في)\b", "*", norm)
    norm = re.sub(r"\b(تقسيم|مقسوم على|على)\b", "/", norm)
    # Handle "ضرب 15 في 4" or "15 في 4"
    norm = re.sub(r"(\d+)\s+في\s+(\d+)", r"\1 * \2", norm)

    # Search for pattern: number operator number
    match = re.search(r"(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)", norm)
    if not match:
        return None

    try:
        a = float(match.group(1))
        op = match.group(2)
        b = float(match.group(3))

        if op == "+":
            res = a + b
        elif op == "-":
            res = a - b
        elif op == "*":
            res = a * b
        elif op == "/":
            if b == 0:
                return "لا يمكن القسمة على صفر."
            res = a / b
        else:
            return None

        if res.is_integer():
            res_str = str(int(res))
        else:
            res_str = f"{res:.2f}".rstrip("0").rstrip(".")

        return f"ناتج العملية هو {res_str}."
    except Exception:
        return None


# =====================================================================
# 6. Branch B Master Dispatcher: handle_general_knowledge
# =====================================================================

def handle_general_knowledge(
    query: str,
    entities: Optional[dict] = None,
    config: Optional[dict] = None,
    force_offline: bool = False,
) -> str:
    """
    Master Dispatcher for Branch B (General Knowledge, Weather, News, Time, Calculations).

    Routes query to:
    - Weather (Open-Meteo)
    - Time (WorldTimeAPI)
    - News (NewsAPI)
    - Math / Calculations (Wolfram Alpha or Safe Math Evaluator)
    - Factual Knowledge / Definitions (DuckDuckGo or Wolfram Alpha)

    100% crash-proof: guarantees returning OFFLINE_FALLBACK_MESSAGE on any network failure.
    """
    if force_offline:
        return OFFLINE_FALLBACK_MESSAGE

    clean_query = (query or "").strip()
    if not clean_query:
        return "يرجى طرح سؤالك وسأساعدك بالإجابة."

    entities = entities or {}
    config = config or {}

    wolfram_id = config.get("wolfram_app_id") or os.environ.get("WOLFRAM_APP_ID", "")
    news_key = config.get("news_api_key") or os.environ.get("NEWS_API_KEY", "")

    try:
        # -------------------------------------------------------------
        # A. Weather Dispatch
        # -------------------------------------------------------------
        is_weather = any(k in clean_query for k in [
            "الطقس", "طقس", "الجو", "جو", "درجة الحرارة", "درجه الحراره",
            "الحرارة في", "الحراره في", "مطر", "أمطار", "امطار", "غيوم", "رياح"
        ]) or entities.get("topic") == "weather" or entities.get("domain") == "weather"

        if is_weather:
            # Extract target city
            city = entities.get("location") or entities.get("city")
            if not city:
                for c in ARABIC_CITIES.keys():
                    if c in clean_query:
                        city = c
                        break
            city = city or "الرياض"
            return query_weather(location_name=city)

        # -------------------------------------------------------------
        # B. Time Dispatch
        # -------------------------------------------------------------
        is_time = any(k in clean_query for k in [
            "كم الساعة", "كم الساعه", "الساعة كم", "الساعه كم",
            "كم الوقت", "الوقت الان", "الوقت الآن", "توقيت",
            "الساعة في", "الساعه في", "الوقت في"
        ]) or entities.get("topic") == "time" or entities.get("domain") == "time"

        if is_time:
            city = entities.get("location") or entities.get("city")
            if not city:
                for c in ARABIC_CITIES.keys():
                    if c in clean_query:
                        city = c
                        break
            city = city or "الرياض"
            return query_time(location_name=city)

        # -------------------------------------------------------------
        # C. News Dispatch
        # -------------------------------------------------------------
        is_news = any(k in clean_query for k in [
            "أخبار", "اخبار", "عناوين الأخبار", "عناوين الاخبار",
            "آخر الأخبار", "اخر الاخبار", "موجز الأخبار", "عاجل",
            "نشرة الأخبار", "نشره الاخبار"
        ]) or entities.get("topic") == "news"

        if is_news:
            topic = entities.get("topic", "")
            if topic == "news":
                topic = ""
            country = entities.get("country", "sa")
            return query_news(topic=topic, country=country, api_key=news_key)

        # -------------------------------------------------------------
        # D. Math / Calculations Dispatch
        # -------------------------------------------------------------
        is_math = any(k in clean_query for k in [
            "احسب", "كم ناتج", "ما ناتج", "ناتج", "زائد", "ناقص",
            "ضرب", "تقسيم", "مجموع"
        ]) or bool(re.search(r"\d+\s*[\+\-\*\/]\s*\d+", clean_query))

        if is_math:
            # Try Wolfram Alpha if configured
            if wolfram_id:
                res_wolfram = query_wolfram(clean_query, app_id=wolfram_id)
                if res_wolfram:
                    return f"الناتج هو {res_wolfram}."

            # Safe local arithmetic evaluator
            res_calc = _safe_calculate_arabic_math(clean_query)
            if res_calc:
                return res_calc

        # -------------------------------------------------------------
        # E. General Fact / Definition (DuckDuckGo -> Wolfram)
        # -------------------------------------------------------------
        ddg_result = query_duckduckgo(clean_query, raise_errors=True)
        if ddg_result:
            return ddg_result

        if wolfram_id:
            wolfram_result = query_wolfram(clean_query, app_id=wolfram_id, raise_errors=True)
            if wolfram_result:
                return wolfram_result

        # Graceful informative fallback when no fact is found
        return "عذراً، لم أتمكن من العثور على معلومات مؤكدة حول هذا الموضوع حالياً."

    except Exception:
        # Ultimate fail-safe: never crash vehicle UI
        return OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# Aliases for Architectural Consistency
# =====================================================================

query_wolfram_alpha = query_wolfram
query_open_meteo = query_weather
query_world_time = query_time
query_newsapi = query_news
