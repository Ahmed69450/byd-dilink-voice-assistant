"""
Tests for Branch B: REST API Clients for Knowledge, Weather, News, and Time.
Covers:
- query_wolfram
- query_duckduckgo
- query_weather & format_weather_response
- query_time & format_time_response
- query_news
- handle_general_knowledge
- 100% crash-proof offline fallback on ConnectionError, Timeout, HTTPError.
"""

import os
from unittest.mock import MagicMock, patch
import pytest
import requests

from api_clients import (
    OFFLINE_FALLBACK_MESSAGE,
    format_weather_response,
    format_time_response,
    query_weather,
    query_time,
    query_news,
    query_duckduckgo,
    query_wolfram,
    handle_general_knowledge,
)


# =====================================================================
# 1. Weather Formatter & Parsing Tests
# =====================================================================

def test_weather_formatter_basic():
    """format_weather_response formats temperature, city, condition, and wind speed."""
    mock_data = {"temperature": 28.5, "weathercode": 0, "windspeed": 12.0}
    res = format_weather_response("الرياض", mock_data)
    assert "28" in res
    assert "الرياض" in res
    assert "صافٍ" in res
    assert "كم/ساعة" in res


def test_weather_formatter_open_meteo_nested_dict():
    """format_weather_response handles raw Open-Meteo nested response format."""
    raw_response = {
        "current_weather": {
            "temperature": 18.0,
            "weathercode": 61,
            "windspeed": 9.5
        }
    }
    res = format_weather_response("عمان", raw_response)
    assert "عمان" in res
    assert "18" in res
    assert "أمطار" in res or "ممطر" in res
    assert "كم/ساعة" in res


def test_weather_formatter_wmo_code_descriptions():
    """WMO codes map accurately to clear Arabic weather conditions."""
    codes_to_test = [
        (0, "صافٍ"),
        (2, "غائم جزئياً"),
        (3, "غائم"),
        (45, "ضباب"),
        (61, "أمطار"),
        (71, "ثلوج"),
        (95, "عواصف رعدية"),
    ]
    for code, expected_fragment in codes_to_test:
        res = format_weather_response("القدس", {"temperature": 20, "weathercode": code, "windspeed": 10})
        assert expected_fragment in res, f"Expected '{expected_fragment}' in response for code {code}, got: {res}"


def test_query_weather_mocked_success():
    """query_weather resolves known Arabic city coordinates and queries Open-Meteo."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current_weather": {
            "temperature": 32.0,
            "weathercode": 0,
            "windspeed": 15.0
        }
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_weather("دبي")
        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "api.open-meteo.com" in call_url
        assert "latitude=" in call_url
        assert "دبي" in res
        assert "32" in res
        assert "صافٍ" in res


def test_query_weather_geocoding_fallback():
    """query_weather uses Open-Meteo geocoding API for unknown/custom locations."""
    mock_geo = MagicMock()
    mock_geo.status_code = 200
    mock_geo.json.return_value = {
        "results": [
            {"latitude": 17.01, "longitude": 54.09, "timezone": "Asia/Muscat", "name": "صلالة"}
        ]
    }

    mock_forecast = MagicMock()
    mock_forecast.status_code = 200
    mock_forecast.json.return_value = {
        "current_weather": {
            "temperature": 26.0,
            "weathercode": 2,
            "windspeed": 8.0
        }
    }

    def side_effect(url, *args, **kwargs):
        if "geocoding-api.open-meteo.com" in url:
            return mock_geo
        return mock_forecast

    with patch("requests.get", side_effect=side_effect):
        res = query_weather("صلالة")
        assert "صلالة" in res
        assert "26" in res
        assert "غائم جزئياً" in res


def test_query_weather_offline_connection_error():
    """query_weather returns graceful Arabic offline message on ConnectionError."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network down")):
        res = query_weather("الرياض")
        assert res == OFFLINE_FALLBACK_MESSAGE


def test_query_weather_offline_timeout():
    """query_weather returns graceful Arabic offline message on Timeout."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Timeout")):
        res = query_weather("جدة")
        assert res == OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# 2. World Time Formatter & Parsing Tests
# =====================================================================

def test_time_formatter_iso_string():
    """format_time_response converts ISO string to natural Arabic time with 24h/12h display."""
    res = format_time_response("دبي", "2026-10-06T14:30:00+04:00")
    assert "دبي" in res
    assert "14:30" in res or "2:30" in res
    assert "مساءً" in res
    assert "الثانية" in res or "النصف" in res


def test_time_formatter_morning_and_evening():
    """format_time_response correctly formats morning, noon, and evening hours."""
    res_am = format_time_response("القاهرة", "2026-10-06T09:15:00+02:00")
    assert "صباحاً" in res_am
    assert "09:15" in res_am or "9:15" in res_am

    res_pm = format_time_response("بغداد", "2026-10-06T20:00:00+03:00")
    assert "مساءً" in res_pm
    assert "20:00" in res_pm or "8:00" in res_pm


def test_query_time_mocked_success():
    """query_time maps city to timezone and queries WorldTimeAPI."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "datetime": "2026-10-07T15:30:00+03:00",
        "timezone": "Asia/Riyadh"
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_time("الرياض")
        assert mock_get.called
        assert "worldtimeapi.org" in mock_get.call_args[0][0]
        assert "الرياض" in res
        assert "15:30" in res
        assert "مساءً" in res


def test_query_time_offline_connection_error():
    """query_time returns graceful Arabic offline message on network failure."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("DNS failure")):
        res = query_time("الرياض")
        assert res == OFFLINE_FALLBACK_MESSAGE


def test_query_time_offline_timeout():
    """query_time returns graceful Arabic offline message on Timeout."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Timeout")):
        res = query_time("طوكيو")
        assert res == OFFLINE_FALLBACK_MESSAGE


# =====================================================================
# 3. NewsAPI Tests
# =====================================================================

def test_query_news_with_api_key_mocked():
    """query_news fetches and formats top 2-3 headlines in spoken Arabic."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {"title": "إطلاق قمر صناعي جديد بنجاح"},
            {"title": "فوز المنتخب الوطني في مباراة اليوم"}
        ]
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_news(topic="رياضة", country="sa", api_key="test_api_key_123")
        assert mock_get.called
        assert "newsapi.org" in mock_get.call_args[0][0]
        assert "إطلاق قمر صناعي جديد بنجاح" in res
        assert "فوز المنتخب الوطني في مباراة اليوم" in res
        assert "أولاً" in res or "عناوين" in res


def test_query_news_missing_api_key():
    """query_news returns helpful Arabic notice when no API key is provided."""
    with patch.dict(os.environ, {}, clear=True):
        res = query_news(api_key="")
        assert "NewsAPI" in res or "مفتاح" in res


def test_query_news_offline_http_error():
    """query_news returns graceful Arabic offline message on HTTPError or network failure."""
    with patch("requests.get", side_effect=requests.exceptions.HTTPError("500 Server Error")):
        res = query_news(api_key="valid_key")
        assert res == OFFLINE_FALLBACK_MESSAGE


def test_query_news_empty_articles():
    """query_news handles empty articles list gracefully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok", "totalResults": 0, "articles": []}

    with patch("requests.get", return_value=mock_resp):
        res = query_news(api_key="valid_key")
        assert "لم يتم العثور على أخبار" in res or "لا توجد أخبار" in res


# =====================================================================
# 4. DuckDuckGo Tests
# =====================================================================

def test_query_duckduckgo_abstract_text():
    """query_duckduckgo extracts AbstractText when available."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "AbstractText": "الرياض هي عاصمة المملكة العربية السعودية وأكبر مدنها.",
        "Answer": "",
        "RelatedTopics": []
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_duckduckgo("عاصمة السعودية")
        assert mock_get.called
        assert "duckduckgo.com" in mock_get.call_args[0][0]
        assert res == "الرياض هي عاصمة المملكة العربية السعودية وأكبر مدنها."


def test_query_duckduckgo_answer_field():
    """query_duckduckgo extracts Answer field when AbstractText is empty."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "AbstractText": "",
        "Answer": "42",
        "RelatedTopics": []
    }

    with patch("requests.get", return_value=mock_resp):
        res = query_duckduckgo("معنى الحياة")
        assert res == "42"


def test_query_duckduckgo_related_topics():
    """query_duckduckgo extracts first RelatedTopic Text when abstract and answer are empty."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "AbstractText": "",
        "Answer": "",
        "RelatedTopics": [
            {"Text": "الذكاء الاصطناعي هو سلوك وخصائص معينة تتسم بها البرامج الحاسوبية."}
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        res = query_duckduckgo("الذكاء الاصطناعي")
        assert res == "الذكاء الاصطناعي هو سلوك وخصائص معينة تتسم بها البرامج الحاسوبية."


def test_query_duckduckgo_offline_returns_none():
    """query_duckduckgo gracefully returns None on network error without crashing."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Offline")):
        res = query_duckduckgo("ما هو البيروني")
        assert res is None


def test_query_duckduckgo_empty_returns_none():
    """query_duckduckgo returns None when no definition or topic is found."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"AbstractText": "", "Answer": "", "RelatedTopics": []}

    with patch("requests.get", return_value=mock_resp):
        res = query_duckduckgo("كلمة غير موجودة بتاتا")
        assert res is None


# =====================================================================
# 5. Wolfram Alpha Tests
# =====================================================================

def test_query_wolfram_with_app_id_success():
    """query_wolfram calls v1/result and returns plain text answer."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "384,400 km"

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_wolfram("distance from earth to moon", app_id="test_app_id")
        assert mock_get.called
        assert "wolframalpha.com" in mock_get.call_args[0][0]
        assert "appid=test_app_id" in mock_get.call_args[0][0]
        assert res == "384,400 km"


def test_query_wolfram_missing_app_id():
    """query_wolfram returns None when no app_id is provided or configured."""
    with patch.dict(os.environ, {}, clear=True):
        res = query_wolfram("2 + 2", app_id="")
        assert res is None


def test_query_wolfram_offline_returns_none():
    """query_wolfram returns None on network error without raising."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Timeout")):
        res = query_wolfram("2 + 2", app_id="valid_app_id")
        assert res is None


def test_query_wolfram_http_error_returns_none():
    """query_wolfram returns None on 501 or non-200 responses."""
    mock_resp = MagicMock()
    mock_resp.status_code = 501
    with patch("requests.get", return_value=mock_resp):
        res = query_wolfram("unknown question", app_id="valid_app_id")
        assert res is None


# =====================================================================
# 6. Master Dispatcher (handle_general_knowledge) Tests
# =====================================================================

def test_handle_general_knowledge_weather_dispatch():
    """handle_general_knowledge dispatches weather query to weather client."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current_weather": {
            "temperature": 29.0,
            "weathercode": 0,
            "windspeed": 10.0
        }
    }

    with patch("requests.get", return_value=mock_resp):
        res = handle_general_knowledge("ما هو الطقس في الرياض اليوم؟")
        assert "الرياض" in res
        assert "29" in res
        assert "صافٍ" in res


def test_handle_general_knowledge_time_dispatch():
    """handle_general_knowledge dispatches time query to time client."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "datetime": "2026-10-07T16:00:00+04:00",
        "timezone": "Asia/Dubai"
    }

    with patch("requests.get", return_value=mock_resp):
        res = handle_general_knowledge("كم الساعة في دبي الآن؟")
        assert "دبي" in res
        assert "16:00" in res or "4:00" in res


def test_handle_general_knowledge_news_dispatch():
    """handle_general_knowledge dispatches news query to news client."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "ok",
        "totalResults": 1,
        "articles": [{"title": "افتتاح مشروع جديد للطاقة المتجددة"}]
    }

    with patch("requests.get", return_value=mock_resp):
        res = handle_general_knowledge("ما هي آخر الأخبار", config={"news_api_key": "dummy_key"})
        assert "افتتاح مشروع جديد للطاقة المتجددة" in res


def test_handle_general_knowledge_calculation_dispatch():
    """handle_general_knowledge calculates math expressions accurately."""
    # Test local/safe calculation for standard arithmetic
    res = handle_general_knowledge("احسب 25 زائد 30")
    assert "55" in res


def test_handle_general_knowledge_multiplication():
    """handle_general_knowledge handles multiplication expressions."""
    res = handle_general_knowledge("ما ناتج ضرب 15 في 4")
    assert "60" in res


def test_handle_general_knowledge_duckduckgo_fact():
    """handle_general_knowledge answers factual queries via DuckDuckGo."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "AbstractText": "باريس هي عاصمة فرنسا وأكبر مدنها من حيث عدد السكان.",
        "Answer": "",
        "RelatedTopics": []
    }

    with patch("requests.get", return_value=mock_resp):
        res = handle_general_knowledge("ما هي عاصمة فرنسا")
        assert "باريس" in res


def test_handle_general_knowledge_force_offline():
    """handle_general_knowledge returns exact Arabic offline message when force_offline=True."""
    res = handle_general_knowledge("ما هو الطقس في القاهرة؟", entities={}, force_offline=True)
    assert res == OFFLINE_FALLBACK_MESSAGE
    assert "إنترنت" in res


def test_handle_general_knowledge_network_exception_fallback():
    """handle_general_knowledge never crashes on network exceptions and returns graceful offline message."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Simulated total network drop")):
        res = handle_general_knowledge("ما هي عاصمة فرنسا")
        assert res == OFFLINE_FALLBACK_MESSAGE


def test_handle_general_knowledge_timeout_fallback():
    """handle_general_knowledge catches timeouts and returns graceful offline message."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Timed out")):
        res = handle_general_knowledge("ما هو الطقس في بيروت؟")
        assert res == OFFLINE_FALLBACK_MESSAGE


def test_handle_general_knowledge_unknown_query_graceful():
    """handle_general_knowledge provides informative answer when search yields nothing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"AbstractText": "", "Answer": "", "RelatedTopics": []}

    with patch("requests.get", return_value=mock_resp):
        res = handle_general_knowledge("xyzfoobar123456789")
        assert res is not None
        assert len(res) > 0
        assert not res.startswith("Error")


# =====================================================================
# 7. Edge Cases & Architectural Robustness Tests
# =====================================================================

def test_query_weather_explicit_coordinates():
    """query_weather uses explicitly provided lat and lon coordinates directly."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current_weather": {
            "temperature": 27.0,
            "weathercode": 0,
            "windspeed": 11.0
        }
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_weather("موقعي الحالي", lat=24.75, lon=46.65)
        call_url = mock_get.call_args[0][0]
        assert "latitude=24.75" in call_url
        assert "longitude=46.65" in call_url
        assert "موقعي الحالي" in res
        assert "27" in res


def test_query_weather_dialectal_city_spelling():
    """query_weather resolves cities with variant spellings (taa marbuta, alef variants)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current_weather": {
            "temperature": 30.0,
            "weathercode": 1,
            "windspeed": 14.0
        }
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        # "القاهره" with haa instead of taa marbuta
        res = query_weather("القاهره")
        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "latitude=30.0444" in call_url


def test_query_time_direct_timezone_string():
    """query_time accepts full timezone identifier directly (e.g. Asia/Dubai)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "datetime": "2026-10-07T11:00:00+04:00",
        "timezone": "Asia/Dubai"
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = query_time(city_or_timezone="Asia/Dubai")
        assert "worldtimeapi.org/api/timezone/Asia/Dubai" in mock_get.call_args[0][0]
        assert "11:00" in res


def test_empty_and_whitespace_queries():
    """Functions gracefully handle empty or whitespace queries without exceptions."""
    assert handle_general_knowledge("   ") == "يرجى طرح سؤالك وسأساعدك بالإجابة."
    assert handle_general_knowledge(None) == "يرجى طرح سؤالك وسأساعدك بالإجابة."
    assert query_duckduckgo("   ") is None
    assert query_wolfram("   ", app_id="test") is None


def test_safe_math_division_by_zero():
    """Division by zero is handled safely with a polite Arabic response."""
    res = handle_general_knowledge("احسب 10 تقسيم 0")
    assert "صفر" in res


def test_architectural_aliases():
    """Aliases match canonical functions for architectural compatibility."""
    import api_clients
    assert api_clients.query_wolfram_alpha is api_clients.query_wolfram
    assert api_clients.query_open_meteo is api_clients.query_weather
    assert api_clients.query_world_time is api_clients.query_time
    assert api_clients.query_newsapi is api_clients.query_news


def test_urllib_fallback_when_requests_disabled():
    """_http_get_json and _http_get_text fall back gracefully to urllib.request."""
    import api_clients
    import json
    import io

    # Mock response object for urllib.request.urlopen
    mock_urlopen_resp = MagicMock()
    mock_urlopen_resp.status = 200
    mock_urlopen_resp.read.return_value = json.dumps({"test": "value"}).encode("utf-8")
    mock_urlopen_resp.__enter__.return_value = mock_urlopen_resp

    with patch.object(api_clients, "HAS_REQUESTS", False):
        with patch("urllib.request.urlopen", return_value=mock_urlopen_resp):
            status, data = api_clients._http_get_json("https://example.com/api", params={"q": "test"})
            assert status == 200
            assert data == {"test": "value"}

    mock_text_resp = MagicMock()
    mock_text_resp.status = 200
    mock_text_resp.read.return_value = "plain text result".encode("utf-8")
    mock_text_resp.__enter__.return_value = mock_text_resp

    with patch.object(api_clients, "HAS_REQUESTS", False):
        with patch("urllib.request.urlopen", return_value=mock_text_resp):
            status, text = api_clients._http_get_text("https://example.com/api")
            assert status == 200
            assert text == "plain text result"
