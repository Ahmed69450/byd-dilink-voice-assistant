"""
Unit tests verifying contract alignment between Python router/car_commands
and the Android Kotlin CarControlBridge, along with Android resource XML validity.
"""

import os
import re
import xml.etree.ElementTree as ET
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAR_COMMANDS_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "python", "car_commands.py")
BRIDGE_KT_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "java", "com", "byd", "voiceassistant", "CarControlBridge.kt")
MANIFEST_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "AndroidManifest.xml")
LAYOUT_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "res", "layout", "activity_main.xml")
STRINGS_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "res", "values", "strings.xml")
COLORS_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "res", "values", "colors.xml")
STYLES_PATH = os.path.join(REPO_ROOT, "android", "app", "src", "main", "res", "values", "styles.xml")


def test_command_constants_match_between_python_and_kotlin():
    """Verify all car command constants in car_commands.py exist in CarControlBridge.kt."""
    assert os.path.isfile(CAR_COMMANDS_PATH), f"Missing {CAR_COMMANDS_PATH}"
    assert os.path.isfile(BRIDGE_KT_PATH), f"Missing {BRIDGE_KT_PATH}"

    with open(CAR_COMMANDS_PATH, "r", encoding="utf-8") as f:
        py_content = f.read()

    with open(BRIDGE_KT_PATH, "r", encoding="utf-8") as f:
        kt_content = f.read()

    # Extract Python constants like AC_ON = "AC_ON"
    py_constants = dict(re.findall(r'^([A-Z][A-Z0-9_]+)\s*=\s*["\']([^"\']+)["\']', py_content, re.MULTILINE))
    assert len(py_constants) >= 20, f"Expected at least 20 commands, found {len(py_constants)}"

    # Extract Kotlin constants like const val AC_ON = "AC_ON"
    kt_constants = dict(re.findall(r'const\s+val\s+([A-Z][A-Z0-9_]+)\s*=\s*["\']([^"\']+)["\']', kt_content))

    # Verify every Python command constant is defined identically in Kotlin
    for cmd_name, cmd_val in py_constants.items():
        assert cmd_name in kt_constants, f"Command {cmd_name} missing in CarControlBridge.kt"
        assert kt_constants[cmd_name] == cmd_val, f"Mismatch for {cmd_name}: Python='{cmd_val}' vs Kotlin='{kt_constants[cmd_name]}'"


def test_parameter_keys_handled_in_kotlin_bridge():
    """Verify parameters extracted by car_commands.py are handled in CarControlBridge.kt."""
    with open(BRIDGE_KT_PATH, "r", encoding="utf-8") as f:
        kt_content = f.read()

    expected_param_keys = [
        "value",
        "temperature",
        "step",
        "speed",
        "destination",
        "app_name",
        "mute",
        "action",
        "window",
    ]

    for key in expected_param_keys:
        assert f'"{key}"' in kt_content, f"Expected parameter key '{key}' to be handled in CarControlBridge.kt"


def test_car_control_bridge_methods():
    """Verify essential methods exist in CarControlBridge.kt."""
    with open(BRIDGE_KT_PATH, "r", encoding="utf-8") as f:
        kt_content = f.read()

    assert "fun executeAction(" in kt_content
    assert "fun sendDiLinkBroadcast(" in kt_content
    assert "interface CarActionListener" in kt_content
    assert "fun setCarActionListener(" in kt_content


def test_android_manifest_validity():
    """Verify AndroidManifest.xml exists and is well-formed XML with required permissions."""
    assert os.path.isfile(MANIFEST_PATH)
    tree = ET.parse(MANIFEST_PATH)
    root = tree.getroot()

    permissions = [elem.attrib.get('{http://schemas.android.com/apk/res/android}name')
                   for elem in root.findall('uses-permission')]

    assert "android.permission.RECORD_AUDIO" in permissions
    assert "android.permission.INTERNET" in permissions
    assert "android.permission.ACCESS_NETWORK_STATE" in permissions
    assert "android.permission.MODIFY_AUDIO_SETTINGS" in permissions

    # Check MainActivity configChanges for screen rotation
    activity = root.find(".//activity[@{http://schemas.android.com/apk/res/android}name='.MainActivity']")
    assert activity is not None
    config_changes = activity.attrib.get('{http://schemas.android.com/apk/res/android}configChanges', '')
    assert "orientation" in config_changes
    assert "screenSize" in config_changes


def test_android_resources_xml_validity():
    """Verify all resource XML files parse without syntax errors."""
    for path in [LAYOUT_PATH, STRINGS_PATH, COLORS_PATH, STYLES_PATH]:
        assert os.path.isfile(path), f"Missing resource file: {path}"
        try:
            ET.parse(path)
        except ET.ParseError as e:
            pytest.fail(f"XML parse error in {path}: {e}")
