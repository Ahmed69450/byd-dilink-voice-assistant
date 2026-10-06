"""
Tests for Master Intent Router, Car Commands, and Chaquopy Entry Points (Task 5).
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from car_commands import (
    AC_ON,
    AC_OFF,
    SET_AC_TEMP,
    AC_TEMP_UP,
    AC_TEMP_DOWN,
    FAN_SPEED,
    WINDOW_OPEN,
    WINDOW_CLOSE,
    WINDOW_FRONT_LEFT,
    WINDOW_ALL,
    SUNROOF_OPEN,
    SUNROOF_CLOSE,
    MEDIA_PLAY,
    MEDIA_PAUSE,
    MEDIA_NEXT,
    MEDIA_PREV,
    VOLUME_UP,
    VOLUME_DOWN,
    VOLUME_SET,
    NAV_TO,
    OPEN_MAPS,
    OPEN_APP,
    DILINK_SETTINGS,
    DILINK_ENERGY_APP,
    DILINK_CAMERA_360,
    map_entities_to_car_action,
)
from router import VoiceAssistantRouter, process_voice_input


# =====================================================================
# 1. Car Commands Mapping Unit Tests
# =====================================================================

def test_car_commands_ac_temperature_set():
    entities = {"target": "ac", "action": "set", "value": 22}
    action, spoken = map_entities_to_car_action(entities, "اضبط المكيف على 22")
    assert action["command"] == SET_AC_TEMP
    assert action["parameters"]["value"] == 22
    assert "22" in spoken
    assert "تكييف" in spoken or "مكيف" in spoken or "حرارة" in spoken


def test_car_commands_ac_turn_on_and_off():
    action_on, spoken_on = map_entities_to_car_action({"target": "ac", "action": "turn_on"}, "شغل المكيف")
    assert action_on["command"] == AC_ON
    assert "تشغيل" in spoken_on or "المكيف" in spoken_on

    action_off, spoken_off = map_entities_to_car_action({"target": "ac", "action": "turn_off"}, "طفي المكيف")
    assert action_off["command"] == AC_OFF
    assert "إيقاف" in spoken_off or "اطفاء" in spoken_off or "المكيف" in spoken_off


def test_car_commands_ac_temperature_up_down():
    action_up, spoken_up = map_entities_to_car_action({"target": "ac", "action": "increase"}, "دفي السيارة")
    assert action_up["command"] == AC_TEMP_UP
    assert len(spoken_up) > 0

    action_down, spoken_down = map_entities_to_car_action({"target": "ac", "action": "decrease"}, "خليه أبرد")
    assert action_down["command"] == AC_TEMP_DOWN
    assert len(spoken_down) > 0


def test_car_commands_ac_fan_speed():
    entities = {"target": "ac", "action": "set", "value": 3}
    action, spoken = map_entities_to_car_action(entities, "حط سرعة المروحة على 3")
    assert action["command"] == FAN_SPEED
    assert action["parameters"]["value"] == 3
    assert "مروحة" in spoken or "3" in spoken


def test_car_commands_windows_and_sunroof():
    action_win_open, _ = map_entities_to_car_action({"target": "window", "action": "open"}, "افتح النوافذ")
    assert action_win_open["command"] == WINDOW_OPEN

    action_win_close, _ = map_entities_to_car_action({"target": "window", "action": "close"}, "سكر الشبابيك")
    assert action_win_close["command"] == WINDOW_CLOSE

    action_driver, _ = map_entities_to_car_action({"target": "window", "action": "open"}, "افتح شباك السائق")
    assert action_driver["command"] == WINDOW_FRONT_LEFT

    action_all_win, _ = map_entities_to_car_action({"target": "window", "action": "open"}, "افتح كل النوافذ")
    assert action_all_win["command"] == WINDOW_ALL

    action_sunroof_open, _ = map_entities_to_car_action({"target": "sunroof", "action": "open"}, "افتح فتحة السقف")
    assert action_sunroof_open["command"] == SUNROOF_OPEN

    action_sunroof_close, _ = map_entities_to_car_action({"target": "sunroof", "action": "close"}, "سكر البانوراما")
    assert action_sunroof_close["command"] == SUNROOF_CLOSE


def test_car_commands_volume_and_media():
    action_vol_up, _ = map_entities_to_car_action({"target": "volume", "action": "increase"}, "علي الصوت")
    assert action_vol_up["command"] == VOLUME_UP

    action_vol_down, _ = map_entities_to_car_action({"target": "volume", "action": "decrease"}, "قصر الصوت")
    assert action_vol_down["command"] == VOLUME_DOWN

    action_vol_set, _ = map_entities_to_car_action({"target": "volume", "action": "set", "value": 15}, "حط الصوت على 15")
    assert action_vol_set["command"] == VOLUME_SET
    assert action_vol_set["parameters"]["value"] == 15

    action_play, _ = map_entities_to_car_action({"target": "media", "action": "turn_on"}, "شغل الموسيقى")
    assert action_play["command"] == MEDIA_PLAY

    action_pause, _ = map_entities_to_car_action({"target": "media", "action": "turn_off"}, "وقف الأغاني")
    assert action_pause["command"] == MEDIA_PAUSE

    action_next, _ = map_entities_to_car_action({"target": "media"}, "المقطع التالي")
    assert action_next["command"] == MEDIA_NEXT

    action_prev, _ = map_entities_to_car_action({"target": "media"}, "المقطع السابق")
    assert action_prev["command"] == MEDIA_PREV


def test_car_commands_navigation_and_apps():
    action_nav, spoken_nav = map_entities_to_car_action({"target": "navigation"}, "وديني المطار")
    assert action_nav["command"] == NAV_TO
    assert "المطار" in action_nav["parameters"].get("destination", "")
    assert "المطار" in spoken_nav

    action_maps, _ = map_entities_to_car_action({"target": "navigation"}, "افتح الخرائط")
    assert action_maps["command"] == OPEN_MAPS

    action_cam, _ = map_entities_to_car_action({"target": "app"}, "افتح كاميرا 360")
    assert action_cam["command"] == DILINK_CAMERA_360

    action_energy, _ = map_entities_to_car_action({"target": "app"}, "افتح شاشة الطاقة")
    assert action_energy["command"] == DILINK_ENERGY_APP

    action_settings, _ = map_entities_to_car_action({"target": "app"}, "افتح الإعدادات")
    assert action_settings["command"] == DILINK_SETTINGS

    action_app, spoken_app = map_entities_to_car_action({"target": "app"}, "افتح تطبيق المتصفح")
    assert action_app["command"] == OPEN_APP
    assert "متصفح" in action_app["parameters"].get("app_name", "").lower()
    assert "متصفح" in spoken_app or "المتصفح" in spoken_app


# =====================================================================
# 2. Master Router Pipeline Tests (Branch A, B, C)
# =====================================================================

def test_full_pipeline_car():
    router = VoiceAssistantRouter()
    out = router.process("شغل المكيف على 20")
    assert isinstance(out, dict)
    assert out["status"] == "success"
    assert out["intent"] == "car_control"
    assert out["car_action"] is not None
    assert out["car_action"]["command"] in [SET_AC_TEMP, AC_ON]
    assert "20" in out["spoken_response"] or "تكييف" in out["spoken_response"]


def test_full_pipeline_chitchat():
    router = VoiceAssistantRouter()
    out = router.process("مرحبا، صباح الخير")
    assert isinstance(out, dict)
    assert out["status"] == "success"
    assert out["intent"] == "chitchat"
    assert len(out["spoken_response"]) > 0
    assert out["car_action"] is None


def test_full_pipeline_general_knowledge():
    router = VoiceAssistantRouter()
    with patch("api_clients.query_weather", return_value="الطقس في الرياض مشمس ودرجة الحرارة 25"):
        out = router.process("كيف الجو في الرياض اليوم؟")
        assert isinstance(out, dict)
        assert out["status"] == "success"
        assert out["intent"] == "general_knowledge"
        assert "الرياض" in out["spoken_response"]
        assert out["car_action"] is None


def test_multi_turn_pipeline_location_resolution():
    router = VoiceAssistantRouter()
    with patch("api_clients.query_time", return_value="الوقت الحالي في مكة المكرمة هو 12:00 ظهراً"), \
         patch("api_clients.query_weather", return_value="درجة الحرارة في مكة 33 درجة مئوية"):
        out1 = router.process("كم الساعة في مكة؟")
        assert out1["intent"] == "general_knowledge"

        out2 = router.process("وكيف الطقس هناك؟")
        assert out2["intent"] == "general_knowledge"
        assert "مكة" in out2["resolved_input"] or "مكه" in out2["resolved_input"]
        assert "33" in out2["spoken_response"] or "مكة" in out2["spoken_response"] or "مكه" in out2["spoken_response"]


def test_multi_turn_pipeline_car_adjustment():
    router = VoiceAssistantRouter()
    out1 = router.process("شغل المكيف")
    assert out1["intent"] == "car_control"

    out2 = router.process("خليه أبرد")
    assert out2["intent"] == "car_control"
    assert out2["car_action"] is not None
    assert out2["car_action"]["command"] == AC_TEMP_DOWN


def test_multi_turn_pipeline_window_continuity():
    router = VoiceAssistantRouter()
    out1 = router.process("افتح النافذة")
    assert out1["intent"] == "car_control"

    out2 = router.process("سكرها")
    assert out2["intent"] == "car_control"
    assert out2["car_action"] is not None
    assert out2["car_action"]["command"] == WINDOW_CLOSE


def test_router_reset_memory():
    router = VoiceAssistantRouter()
    router.process("كم الساعة في جدة؟")
    assert router.memory.get_context_entity("location") in ["جدة", "جده"]

    router.reset_memory()
    assert router.memory.get_context_entity("location") is None
    assert router.memory.turn_count == 0


def test_empty_and_whitespace_input():
    router = VoiceAssistantRouter()
    out_empty = router.process("")
    assert out_empty["status"] == "success"
    assert len(out_empty["spoken_response"]) > 0
    assert out_empty["car_action"] is None

    out_spaces = router.process("    \n\t  ")
    assert out_spaces["status"] == "success"
    assert len(out_spaces["spoken_response"]) > 0


def test_crash_proof_graceful_error_handling():
    router = VoiceAssistantRouter()
    with patch.object(router, "_classify_with_memory", side_effect=RuntimeError("Simulated failure")):
        out = router.process("شغل المكيف")
        assert out["status"] == "error"
        assert "عذراً" in out["spoken_response"] or "خطأ" in out["spoken_response"]
        assert out["error"] is not None


# =====================================================================
# 3. Chaquopy JSON Serialization Tests
# =====================================================================

def test_process_voice_input_json_output():
    json_str = process_voice_input("شغل المكيف على 22")
    assert isinstance(json_str, str)

    parsed = json.loads(json_str)
    assert parsed["status"] == "success"
    assert parsed["intent"] == "car_control"
    assert parsed["raw_input"] == "شغل المكيف على 22"
    assert parsed["car_action"]["command"] in [SET_AC_TEMP, AC_ON]
    assert parsed["car_action"]["parameters"]["value"] == 22
    assert "22" in parsed["spoken_response"] or "تكييف" in parsed["spoken_response"]
    assert parsed["error"] is None


def test_process_voice_input_with_custom_config():
    custom_cfg = json.dumps({"wolfram_app_id": "test_app_id", "news_api_key": "test_news_key"})
    json_str = process_voice_input("صباح الخير", config_json=custom_cfg)
    parsed = json.loads(json_str)
    assert parsed["status"] == "success"
    assert parsed["intent"] == "chitchat"
    assert len(parsed["spoken_response"]) > 0


def test_process_voice_input_invalid_json_config():
    # Should not crash if invalid JSON config string is provided
    json_str = process_voice_input("مرحبا", config_json="{invalid_json")
    parsed = json.loads(json_str)
    assert parsed["status"] == "success"
    assert parsed["intent"] == "chitchat"


# =====================================================================
# 4. CLI Simulation Script Tests
# =====================================================================

def test_cli_script_query_mode():
    cli_path = Path(__file__).resolve().parent.parent / "scripts" / "test_router_cli.py"
    res = subprocess.run(
        [sys.executable, str(cli_path), "--query", "شغل المكيف على 21"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "car_control" in res.stdout
    assert "SET_AC_TEMP" in res.stdout or "AC_ON" in res.stdout


def test_cli_script_demo_mode():
    cli_path = Path(__file__).resolve().parent.parent / "scripts" / "test_router_cli.py"
    res = subprocess.run(
        [sys.executable, str(cli_path), "--demo"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "خليه أبرد" in res.stdout or "AC_TEMP_DOWN" in res.stdout
    assert "وهناك" in res.stdout or "مكة" in res.stdout or "الرياض" in res.stdout


def test_cli_script_interactive_exit():
    cli_path = Path(__file__).resolve().parent.parent / "scripts" / "test_router_cli.py"
    res = subprocess.run(
        [sys.executable, str(cli_path), "--interactive"],
        input="exit\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "مع السلامة" in res.stdout


def test_cli_script_interactive_query_and_reset():
    cli_path = Path(__file__).resolve().parent.parent / "scripts" / "test_router_cli.py"
    res = subprocess.run(
        [sys.executable, str(cli_path), "--interactive"],
        input="شغل المكيف\nreset\nexit\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "AC_ON" in res.stdout or "car_control" in res.stdout
    assert "تم تصفير ذاكرة السياق" in res.stdout


def test_cli_script_default_invocation():
    cli_path = Path(__file__).resolve().parent.parent / "scripts" / "test_router_cli.py"
    res = subprocess.run(
        [sys.executable, str(cli_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "Demo Mode" in res.stdout or "السيناريو" in res.stdout


def test_mixed_multiturn_dialogue():
    router = VoiceAssistantRouter()
    # Turn 1: Car command
    r1 = router.process("افتح فتحة السقف")
    assert r1["intent"] == "car_control"
    assert r1["car_action"]["command"] == SUNROOF_OPEN

    # Turn 2: Chitchat
    r2 = router.process("شكراً لك")
    assert r2["intent"] == "chitchat"
    assert len(r2["spoken_response"]) > 0

    # Turn 3: General knowledge (Math)
    r3 = router.process("كم ناتج 15 زائد 25؟")
    assert r3["intent"] == "general_knowledge"
    assert "40" in r3["spoken_response"]

    # Turn 4: Close the sunroof via pronoun
    r4 = router.process("سكرها")
    assert r4["intent"] == "car_control"
    assert r4["car_action"]["command"] == SUNROOF_CLOSE


def test_chitchat_fallback_response():
    router = VoiceAssistantRouter()
    r = router.process("أكلت اليوم تفاحة خضراء لذيذة جداً")
    assert r["intent"] == "chitchat"
    assert r["status"] == "success"
    assert len(r["spoken_response"]) > 0
    assert r["car_action"] is None


def test_custom_chitchat_path_initialization(tmp_path):
    custom_chitchat_file = tmp_path / "custom_chitchat.json"
    custom_data = [
        {
            "pattern": "من أنت يا هذا",
            "aliases": ["مين انت يا هذا"],
            "responses": ["أنا مساعد مخصص للاختبار!"]
        }
    ]
    custom_chitchat_file.write_text(json.dumps(custom_data, ensure_ascii=False), encoding="utf-8")

    router = VoiceAssistantRouter(chitchat_path=str(custom_chitchat_file))
    r = router.process("من أنت يا هذا")
    assert r["intent"] == "chitchat"
    assert "مساعد مخصص للاختبار" in r["spoken_response"]

