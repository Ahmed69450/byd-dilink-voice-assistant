"""
Tests for Branch C: Arabic Chitchat Engine and Kaggle Dataset Script.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

# Ensure python modules can be imported
from chitchat_engine import ChitchatEngine, levenshtein_similarity


# =====================================================================
# ChitchatEngine Core Unit Tests
# =====================================================================

def test_engine_init_default():
    """Engine initializes with default assets/chitchat.json and size > 0."""
    engine = ChitchatEngine()
    assert engine.size() > 0
    assert len(engine.patterns) > 0


def test_engine_init_custom_path(tmp_path):
    """Engine loads custom dataset correctly."""
    custom_data = [
        {
            "pattern": "مرحبا يا كمبيوتر",
            "aliases": ["اهلا كمبيوتر"],
            "responses": ["مرحبا بك يا مستخدم!"]
        }
    ]
    custom_file = tmp_path / "custom_chitchat.json"
    custom_file.write_text(json.dumps(custom_data, ensure_ascii=False), encoding="utf-8")

    engine = ChitchatEngine(data_path=str(custom_file))
    assert engine.size() == 1
    resp = engine.get_response("مرحبا يا كمبيوتر")
    assert resp == "مرحبا بك يا مستخدم!"


def test_levenshtein_similarity():
    """levenshtein_similarity returns 1.0 for identical strings and near 0.0 for distinct strings."""
    assert levenshtein_similarity("صباح الخير", "صباح الخير") == pytest.approx(1.0)
    assert levenshtein_similarity("صباح الخير", "صباح النور") > 0.5
    assert levenshtein_similarity("abc", "xyz") == pytest.approx(0.0)
    assert levenshtein_similarity("", "") == pytest.approx(1.0)
    assert levenshtein_similarity("مرحبا", "") == pytest.approx(0.0)


def test_chitchat_exact_matches():
    """Engine returns matching response for exact canonical patterns."""
    engine = ChitchatEngine()

    # Greeting
    res1 = engine.get_response("صباح الخير")
    assert res1 is not None
    assert any(term in res1 for term in ["صباح", "الخير", "النور", "الورد", "يسعد"])

    # Identity
    res2 = engine.get_response("من أنت")
    assert res2 is not None
    assert any(term in res2 for term in ["مساعد", "BYD", "بي واي دي", "DiLink"])

    # Gratitude
    res3 = engine.get_response("شكرا")
    assert res3 is not None
    assert any(term in res3 for term in ["العفو", "خدمتك", "أهلاً", "اهلا", "سعة", "يعافيك", "يسلمك", "الرحب"])


def test_chitchat_alias_matches():
    """Engine matches dialectal and synonymous aliases."""
    engine = ChitchatEngine()

    # Aliases for "من أنت"
    res1 = engine.get_response("مين انت")
    assert res1 is not None
    assert any(term in res1 for term in ["مساعد", "BYD", "بي واي دي", "DiLink"])

    res2 = engine.get_response("عرفني بنفسك")
    assert res2 is not None

    # Aliases for "كيف حالك"
    res3 = engine.get_response("شلونك")
    assert res3 is not None

    res4 = engine.get_response("شخبارك")
    assert res4 is not None

    res5 = engine.get_response("ازيك")
    assert res5 is not None


def test_chitchat_fuzzy_matches():
    """Engine handles phrasing with extra words, dialect suffixes, and minor typos."""
    engine = ChitchatEngine()

    # Extra words added
    res1 = engine.get_response("مين انت يا رفيقي المساعد")
    assert res1 is not None
    assert any(term in res1 for term in ["مساعد", "BYD", "بي واي دي", "DiLink"])

    res2 = engine.get_response("صباح الخير يا غالي")
    assert res2 is not None

    res3 = engine.get_response("احكيلي نكتة حلوة تضحك")
    assert res3 is not None

    res4 = engine.get_response("يعطيك الف عافيه وما قصرت")
    assert res4 is not None


def test_chitchat_normalization_robustness():
    """Engine matches even with heavy tashkeel, different alefs, and punctuation."""
    engine = ChitchatEngine()

    # Tashkeel + punctuation
    res1 = engine.get_response("صَبَاحُ الخَيْرِ؟!")
    assert res1 is not None

    # Alef variants
    res2 = engine.get_response("إحكي لي نكتة")
    assert res2 is not None

    # Taa marbuta variation
    res3 = engine.get_response("نكته")
    assert res3 is not None


def test_chitchat_low_confidence_unrelated_query():
    """Engine returns None (or fallback) for queries that don't match any chitchat pattern."""
    engine = ChitchatEngine()

    # Random nonsense or unrelated queries
    assert engine.get_response("xyzqwerty123456") is None
    assert engine.get_response("شغل محرك الصاروخ الفضائي إلى المريخ") is None

    # Test fallback parameter
    fallback = "أنا هنا لمساعدتك في سيارتك بي واي دي!"
    res_fb = engine.get_response("xyzqwerty123456", fallback=fallback)
    assert res_fb == fallback


def test_chitchat_threshold_control():
    """Strict threshold rejects loose matches while standard threshold accepts them."""
    engine = ChitchatEngine()
    query = "صباح الخير يا قمر وسكر"

    # With high threshold (e.g. 0.98), partial match shouldn't qualify
    res_strict = engine.get_response(query, threshold=0.98)
    assert res_strict is None

    # With standard threshold (0.55), it matches "صباح الخير"
    res_normal = engine.get_response(query, threshold=0.55)
    assert res_normal is not None


def test_get_best_match():
    """get_best_match returns tuple of (matching_dict, score)."""
    engine = ChitchatEngine()

    best_item, score = engine.get_best_match("من أنت")
    assert best_item is not None
    assert "responses" in best_item
    assert score >= 0.95

    # Completely unrelated query
    unrelated_item, unrelated_score = engine.get_best_match("abcdefghijklmnop")
    assert unrelated_score < 0.35

    # Empty query
    empty_item, empty_score = engine.get_best_match("")
    assert empty_score == 0.0
    assert empty_item is None


def test_chitchat_response_randomness():
    """Engine picks randomly from available responses for a pattern."""
    engine = ChitchatEngine()
    # Gather responses for "من أنت" across 20 calls
    responses = {engine.get_response("من أنت") for _ in range(25)}
    # If the item has multiple responses, we should observe more than 1 distinct response
    best_item, _ = engine.get_best_match("من أنت")
    if len(best_item.get("responses", [])) > 1:
        assert len(responses) > 1


def test_engine_performance_sub_50ms():
    """Engine query response time is well below 50ms per query."""
    engine = ChitchatEngine()
    queries = [
        "صباح الخير",
        "كيف حالك اليوم",
        "مين انت",
        "شكرا جزيلا",
        "احكيلي نكتة",
        "مع السلامة",
        "شو مميزات سيارتي",
        "أنا طفشان",
    ] * 5  # 40 queries total

    start = time.perf_counter()
    for q in queries:
        engine.get_response(q)
    total_time = time.perf_counter() - start

    avg_time_ms = (total_time / len(queries)) * 1000
    assert avg_time_ms < 50.0, f"Average query took {avg_time_ms:.2f}ms (> 50ms)"


def test_chitchat_json_categories_coverage():
    """Verify standard chitchat.json contains key automotive & conversational categories."""
    engine = ChitchatEngine()
    patterns_text = " ".join([p.get("pattern", "") + " " + " ".join(p.get("aliases", [])) for p in engine.patterns])

    # Must contain greetings
    assert any(w in patterns_text for w in ["صباح الخير", "مساء الخير", "السلام عليكم", "مرحبا"])
    # Must contain well-being
    assert any(w in patterns_text for w in ["كيف حالك", "شخبارك", "كيفك", "شلونك"])
    # Must contain vehicle identity
    assert any(w in patterns_text for w in ["سيارتي", "بي واي دي", "BYD", "مميزات"])
    # Must contain jokes/banter
    assert any(w in patterns_text for w in ["نكتة", "نكته", "طفشان", "ملل"])
    # Must contain travel pleasantries
    assert any(w in patterns_text for w in ["سلامة", "سلامه", "طريق", "وين نروح"])


# =====================================================================
# Kaggle Fetch Script Unit Tests
# =====================================================================

def test_kaggle_script_clean_text():
    """Scripts module cleans Arabic strings properly."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import fetch_kaggle_chitchat

    raw = "  <b>مرحبا!!</b>  \n كيف حالك؟؟  "
    cleaned = fetch_kaggle_chitchat.clean_text(raw)
    assert "<b>" not in cleaned
    assert "مرحبا" in cleaned
    assert "كيف حالك" in cleaned


def test_kaggle_script_parse_csv(tmp_path):
    """Scripts module parses raw CSV dataset with questions and answers."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import fetch_kaggle_chitchat

    csv_file = tmp_path / "raw_chitchat.csv"
    csv_file.write_text(
        "question,answer\n"
        "صباح الورد,صباح الفل والياسمين!\n"
        "كيف صحتك,الحمد لله بأفضل حال.\n"
        "صباح الورد,أهلاً بك وصباحك سعيد!\n",
        encoding="utf-8"
    )

    items = fetch_kaggle_chitchat.parse_dataset_file(str(csv_file))
    assert len(items) == 2  # "صباح الورد" merged with 2 responses

    morning_item = next(it for it in items if it["pattern"] == "صباح الورد")
    assert len(morning_item["responses"]) == 2


def test_kaggle_script_merge_into_json(tmp_path):
    """Scripts module can merge new dialogue items into existing chitchat.json."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import fetch_kaggle_chitchat

    base_json = tmp_path / "chitchat.json"
    initial_data = [
        {
            "pattern": "من أنت",
            "aliases": ["مين انت"],
            "responses": ["مساعد بي واي دي"]
        }
    ]
    base_json.write_text(json.dumps(initial_data, ensure_ascii=False), encoding="utf-8")

    new_items = [
        {
            "pattern": "من أنت",
            "aliases": ["ما اسمك"],
            "responses": ["أنا نظام BYD الذكي"]
        },
        {
            "pattern": "صباح الخير",
            "aliases": [],
            "responses": ["صباح النور"]
        }
    ]

    merged = fetch_kaggle_chitchat.merge_datasets(str(base_json), new_items)
    assert len(merged) == 2

    # "من أنت" should now have both responses and merged aliases
    who_item = next(it for it in merged if it["pattern"] == "من أنت")
    assert len(who_item["responses"]) == 2
    assert "ما اسمك" in who_item["aliases"]
    assert "مين انت" in who_item["aliases"]


def test_engine_nonexistent_file_raises():
    """Engine raises FileNotFoundError when given non-existent custom path."""
    with pytest.raises(FileNotFoundError):
        ChitchatEngine(data_path="nonexistent_file_12345.json")


def test_kaggle_script_parse_json_and_tsv(tmp_path):
    """Scripts module parses JSON format and TSV format correctly."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import fetch_kaggle_chitchat

    # Test TSV
    tsv_file = tmp_path / "raw_data.tsv"
    tsv_file.write_text("prompt\treply\nوين نروح اليوم\tنقدر نروح البحر!\n", encoding="utf-8")
    tsv_items = fetch_kaggle_chitchat.parse_dataset_file(str(tsv_file))
    assert len(tsv_items) == 1
    assert tsv_items[0]["pattern"] == "وين نروح اليوم"
    assert "نقدر نروح البحر!" in tsv_items[0]["responses"]

    # Test JSON list of question/answer dicts
    json_file = tmp_path / "raw_qa.json"
    qa_list = [
        {"سؤال": "كيف الجو", "جواب": "الجو جميل اليوم"},
        {"سؤال": "شو رايك", "جواب": "فكرة ممتازة"}
    ]
    json_file.write_text(json.dumps(qa_list, ensure_ascii=False), encoding="utf-8")
    json_items = fetch_kaggle_chitchat.parse_dataset_file(str(json_file))
    assert len(json_items) == 2


def test_kaggle_script_cli_execution(tmp_path):
    """Scripts CLI runs successfully via subprocess."""
    import subprocess

    input_csv = tmp_path / "cli_input.csv"
    input_csv.write_text("question,answer\nمرحبا,أهلاً بك\n", encoding="utf-8")
    output_json = tmp_path / "cli_output.json"

    script_path = Path(__file__).resolve().parent.parent / "scripts" / "fetch_kaggle_chitchat.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--input", str(input_csv),
        "--output", str(output_json)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert res.returncode == 0
    assert output_json.is_file()

    with open(output_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 1
    assert loaded[0]["pattern"] == "مرحبا"


def test_chitchat_negative_car_commands():
    """Car commands like 'شغل المحرك' and 'تبريد' do not trigger chitchat (score < 0.55)."""
    engine = ChitchatEngine()

    # "شغل المحرك" (car command: start engine) must score < 0.55 and return None
    best_item_engine, score_engine = engine.get_best_match("شغل المحرك")
    assert score_engine < 0.55, f"Expected score < 0.55 for 'شغل المحرك', got {score_engine}"
    assert engine.get_response("شغل المحرك") is None

    # "تبريد" (car command: cooling) must score < 0.55 and return None
    best_item_cool, score_cool = engine.get_best_match("تبريد")
    assert score_cool < 0.55, f"Expected score < 0.55 for 'تبريد', got {score_cool}"
    assert engine.get_response("تبريد") is None


def test_chitchat_negative_short_particles():
    """Short particles like 'لا', 'شو', 'هل', 'ما' return None."""
    engine = ChitchatEngine()
    particles = ["لا", "شو", "هل", "ما"]

    for particle in particles:
        _, score = engine.get_best_match(particle)
        assert score < 0.55, f"Particle '{particle}' scored {score} >= 0.55"
        assert engine.get_response(particle) is None


def test_kaggle_script_preserve_aliases_formatted_json(tmp_path):
    """Preserves and merges aliases when formatting/merging JSON files."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import fetch_kaggle_chitchat

    json_file = tmp_path / "formatted_input.json"
    data = [
        {
            "pattern": "من أنت",
            "aliases": ["مين انت", "عرفني بنفسك"],
            "responses": ["أنا المساعد الصوتي بي واي دي"]
        },
        {
            "pattern": "من أنت",
            "aliases": ["ما اسمك"],
            "responses": ["أنا رفيقك الصوتي"]
        }
    ]
    json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    parsed = fetch_kaggle_chitchat.parse_dataset_file(str(json_file))
    assert len(parsed) == 1
    item = parsed[0]
    assert item["pattern"] == "من أنت"
    assert "مين انت" in item["aliases"]
    assert "عرفني بنفسك" in item["aliases"]
    assert "ما اسمك" in item["aliases"]
    assert len(item["responses"]) == 2


def test_kaggle_script_overwrite_protection(tmp_path):
    """Scripts CLI prevents accidental overwriting of existing output file without --merge or --overwrite."""
    import subprocess

    input_csv = tmp_path / "in.csv"
    input_csv.write_text("question,answer\nمرحبا,أهلاً بك\n", encoding="utf-8")
    existing_output = tmp_path / "existing.json"
    existing_output.write_text("[]", encoding="utf-8")

    script_path = Path(__file__).resolve().parent.parent / "scripts" / "fetch_kaggle_chitchat.py"

    # Running without --merge or --overwrite must fail (exit code 1)
    cmd_fail = [
        sys.executable,
        str(script_path),
        "--input", str(input_csv),
        "--output", str(existing_output)
    ]
    res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
    assert res_fail.returncode == 1
    assert "already exists" in res_fail.stdout or "already exists" in res_fail.stderr

    # Running with --overwrite must succeed
    cmd_ok = [
        sys.executable,
        str(script_path),
        "--input", str(input_csv),
        "--output", str(existing_output),
        "--overwrite"
    ]
    res_ok = subprocess.run(cmd_ok, capture_output=True, text=True)
    assert res_ok.returncode == 0


def test_kaggle_script_local_file_alias(tmp_path):
    """Scripts CLI accepts --local-file alias as input and merges cleanly."""
    import subprocess

    sample_csv = tmp_path / "sample.csv"
    sample_csv.write_text("question,answer\nيا هلا,أهلاً وسهلاً بك يا مرحبا!\n", encoding="utf-8")

    existing_json = tmp_path / "merged_out.json"
    existing_json.write_text(json.dumps([{"pattern": "صباح الخير", "responses": ["صباح النور"]}]), encoding="utf-8")

    script_path = Path(__file__).resolve().parent.parent / "scripts" / "fetch_kaggle_chitchat.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--local-file", str(sample_csv),
        "--output", str(existing_json),
        "--merge"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    with open(existing_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert any(it.get("pattern") == "يا هلا" for it in loaded)


def test_bundled_python_chitchat_json_exists():
    """Verify chitchat.json is bundled in python source directory and matches assets."""
    repo_root = Path(__file__).resolve().parent.parent
    python_json = repo_root / "android" / "app" / "src" / "main" / "python" / "chitchat.json"
    assets_json = repo_root / "android" / "app" / "src" / "main" / "assets" / "chitchat.json"

    assert python_json.is_file(), f"Missing bundled {python_json}"
    assert assets_json.is_file(), f"Missing assets {assets_json}"

    with open(python_json, "r", encoding="utf-8") as f1, open(assets_json, "r", encoding="utf-8") as f2:
        py_data = json.load(f1)
        as_data = json.load(f2)

    assert len(py_data) > 0
    assert py_data == as_data


def test_chitchat_engine_loads_bundled_python_chitchat_first():
    """Verify ChitchatEngine default resolution prioritizes python dir chitchat.json."""
    engine = ChitchatEngine()
    repo_root = Path(__file__).resolve().parent.parent
    expected_bundled = repo_root / "android" / "app" / "src" / "main" / "python" / "chitchat.json"

    # Engine size must match bundled file count
    with open(expected_bundled, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert engine.size() == len(data)



