"""
Tests for FSMMemory: FSM Context Memory & Coreference Resolution.
"""

import time
import threading
import pytest
from fsm_memory import FSMMemory


def test_fsm_initial_state():
    """Initial FSMMemory instance should be idle and unexpired."""
    memory = FSMMemory()
    assert not memory.is_expired()
    assert memory.turn_count == 0
    assert memory.get_context_entity("location") is None
    assert memory.get_context_entity("target") is None
    topic = memory.get_last_topic()
    assert topic["state"] == "idle"
    assert topic["intent"] is None
    assert topic["entities"] == {}


def test_fsm_update_and_get_last_topic():
    """Updating memory updates state, intent, entities, and turn count."""
    memory = FSMMemory()
    intent_data = {
        "intent": "general_knowledge",
        "confidence": 0.94,
        "entities": {"location": "باريس", "raw_text": "كم الساعة في باريس؟"},
    }
    response_data = {"spoken_response": "الساعة في باريس هي 10 صباحاً"}

    memory.update("كم الساعة في باريس؟", intent_data, response_data)

    assert not memory.is_expired()
    assert memory.turn_count == 1
    assert memory.get_context_entity("location") == "باريس"
    assert memory.get_context_entity("state") == "general_knowledge"
    assert memory.get_context_entity("intent") == "general_knowledge"

    topic = memory.get_last_topic()
    assert topic["state"] == "general_knowledge"
    assert topic["intent"] == "general_knowledge"
    assert topic["entities"].get("location") == "باريس"
    assert topic["turn_count"] == 1


def test_fsm_pronoun_resolution_locative_honak():
    """Resolves 'هناك' to the previously tracked location."""
    memory = FSMMemory()
    # Turn 1
    memory.update(
        "كم الساعة في باريس؟",
        {"intent": "general_knowledge", "entities": {"location": "باريس"}},
        {},
    )
    # Turn 2 with pronoun/locative reference
    resolved = memory.resolve_references("ما هو الطقس هناك؟")
    assert "باريس" in resolved


def test_fsm_pronoun_resolution_locative_fiha():
    """Resolves 'وفيها' / 'فيها' to reference the city in context."""
    memory = FSMMemory()
    # Turn 1
    memory.update(
        "كيف الجو في دبي؟",
        {"intent": "general_knowledge", "entities": {"location": "دبي"}},
        {},
    )
    # Turn 2 with locative pronoun
    resolved = memory.resolve_references("وفيها مطر؟")
    assert "دبي" in resolved


def test_fsm_pronoun_resolution_locative_nafs_al_makan():
    """Resolves 'بنفس المكان' / 'نفس المكان' to the previously mentioned city."""
    memory = FSMMemory()
    memory.update(
        "كم تبعد الرياض؟",
        {"intent": "general_knowledge", "entities": {"location": "الرياض"}},
        {},
    )
    resolved = memory.resolve_references("ما هو الطقس بنفس المكان؟")
    assert "الرياض" in resolved


def test_fsm_car_adjustment_context_ac_khaleeh_abrad():
    """Resolves 'خليه أبرد' to associate with the AC target in context."""
    memory = FSMMemory()
    memory.update(
        "شغل التكييف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
        {},
    )
    resolved = memory.resolve_references("خليه أبرد")
    assert "تكييف" in resolved


def test_fsm_car_command_continuity_sakirha():
    """Resolves 'سكرها' following window control to close the window."""
    memory = FSMMemory()
    memory.update(
        "افتح النافذة",
        {"intent": "car_control", "entities": {"target": "window", "action": "open"}},
        {},
    )
    resolved = memory.resolve_references("سكرها")
    assert ("النافذة" in resolved) or ("نافذة" in resolved) or ("شباك" in resolved)


def test_fsm_car_command_continuity_aleeh_shwaya():
    """Resolves 'عليه شوية' to increase the volume when volume was active."""
    memory = FSMMemory()
    memory.update(
        "علي الصوت",
        {"intent": "car_control", "entities": {"target": "volume", "action": "increase"}},
        {},
    )
    resolved = memory.resolve_references("عليه شوية")
    assert "الصوت" in resolved


def test_fsm_car_command_continuity_sunroof():
    """Resolves 'قفلها' or 'سكرها' following sunroof command."""
    memory = FSMMemory()
    memory.update(
        "افتح فتحة السقف",
        {"intent": "car_control", "entities": {"target": "sunroof", "action": "open"}},
        {},
    )
    resolved = memory.resolve_references("قفلها")
    assert ("فتحة السقف" in resolved) or ("سقف" in resolved)


def test_fsm_car_command_continuity_turn_off_pronoun():
    """Resolves 'طفه' or 'طفيه' to turn off active device."""
    memory = FSMMemory()
    memory.update(
        "شغل المكيف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
        {},
    )
    resolved = memory.resolve_references("طفه")
    assert ("تكييف" in resolved) or ("مكيف" in resolved)


def test_fsm_car_pronoun_lahu():
    """Resolves 'وطي له' or 'قصر له' to target in context."""
    memory = FSMMemory()
    memory.update(
        "شغل التكييف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
        {},
    )
    resolved = memory.resolve_references("وطي له")
    assert ("تكييف" in resolved) or ("مكيف" in resolved)


def test_fsm_car_pronoun_nafsahu():
    """Resolves 'نفسه' to the previous car target."""
    memory = FSMMemory()
    memory.update(
        "شغل المكيف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
        {},
    )
    resolved = memory.resolve_references("طفي نفسه")
    assert ("تكييف" in resolved) or ("مكيف" in resolved)


def test_fsm_implicit_location_continuity():
    """If follow-up question has no location, injects stored location."""
    memory = FSMMemory()
    memory.update(
        "كم الساعة في لندن؟",
        {"intent": "general_knowledge", "entities": {"location": "لندن"}},
        {},
    )
    resolved = memory.resolve_references("وكيف الطقس؟")
    assert "لندن" in resolved


def test_fsm_explicit_entity_overrides_reference():
    """If follow-up utterance specifies a new location, memory reference is not injected."""
    memory = FSMMemory()
    memory.update(
        "كم الساعة في باريس؟",
        {"intent": "general_knowledge", "entities": {"location": "باريس"}},
        {},
    )
    resolved = memory.resolve_references("ما هو الطقس في طوكيو؟")
    assert "طوكيو" in resolved
    assert "باريس" not in resolved


def test_fsm_session_timeout_expiry():
    """When session times out, references are not resolved and memory resets to idle."""
    memory = FSMMemory(session_timeout_seconds=60.0)
    memory.update(
        "كم الساعة في باريس؟",
        {"intent": "general_knowledge", "entities": {"location": "باريس"}},
        {},
    )
    assert not memory.is_expired()

    # Simulate timeout by backdating timestamp
    memory.last_timestamp -= 100.0
    assert memory.is_expired() is True

    # Resolving references after expiry should not resolve
    resolved = memory.resolve_references("ما هو الطقس هناك؟")
    assert resolved == "ما هو الطقس هناك؟"
    assert memory.get_context_entity("location") is None

    topic = memory.get_last_topic()
    assert topic["state"] == "idle"


def test_fsm_reset():
    """Reset clears all context state and entities."""
    memory = FSMMemory()
    memory.update(
        "شغل التكييف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
        {},
    )
    assert memory.get_context_entity("target") == "ac"

    memory.reset()
    assert memory.get_context_entity("target") is None
    assert memory.get_context_entity("location") is None
    assert memory.turn_count == 0
    assert memory.get_last_topic()["state"] == "idle"


def test_fsm_multiturn_conversation_flow():
    """Tests a complex multi-turn conversation switching between knowledge and car control."""
    memory = FSMMemory()

    # Turn 1: Knowledge with Cairo
    memory.update(
        "كم الساعة في القاهرة؟",
        {"intent": "general_knowledge", "entities": {"location": "القاهرة"}},
    )
    assert memory.get_context_entity("location") == "القاهرة"

    # Turn 2: Follow-up with 'هناك'
    res2 = memory.resolve_references("ما هو الطقس هناك؟")
    assert "القاهرة" in res2
    memory.update(
        res2,
        {"intent": "general_knowledge", "entities": {"location": "القاهرة"}},
    )

    # Turn 3: Follow-up with 'وفيها'
    res3 = memory.resolve_references("وفيها مطر؟")
    assert "القاهرة" in res3

    # Turn 4: Switch to Car Control
    memory.update(
        "شغل التكييف على 22",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on", "value": 22}},
    )
    assert memory.get_context_entity("target") == "ac"
    assert memory.get_context_entity("value") == 22

    # Turn 5: AC continuity 'خليه أبرد'
    res5 = memory.resolve_references("خليه أبرد")
    assert "تكييف" in res5
    memory.update(
        res5,
        {"intent": "car_control", "entities": {"target": "ac", "action": "decrease"}},
    )

    # Turn 6: Switch target to window
    memory.update(
        "افتح الشباك",
        {"intent": "car_control", "entities": {"target": "window", "action": "open"}},
    )
    assert memory.get_context_entity("target") == "window"

    # Turn 7: Window continuity 'سكره'
    res7 = memory.resolve_references("سكره")
    assert ("شباك" in res7) or ("نافذة" in res7) or ("النافذة" in res7)


def test_fsm_empty_and_none_handling():
    """Handles empty or None strings gracefully."""
    memory = FSMMemory()
    assert memory.resolve_references("") == ""
    assert memory.resolve_references(None) == ""
    memory.update("", {})
    assert memory.turn_count == 1


def test_fsm_no_prior_context_resolution():
    """If no prior context exists, utterances with references remain unchanged."""
    memory = FSMMemory()
    res1 = memory.resolve_references("ما هو الطقس هناك؟")
    assert res1 == "ما هو الطقس هناك؟"
    res2 = memory.resolve_references("خليه أبرد")
    assert res2 == "خليه أبرد"
    res3 = memory.resolve_references("سكرها")
    assert res3 == "سكرها"


def test_fsm_auto_extraction_of_location_and_device():
    """Verifies that update automatically extracts location or device if not in entities."""
    memory = FSMMemory()
    # Location auto-detected from raw text
    memory.update("كم الساعة في المنامة؟", {"intent": "general_knowledge"})
    assert memory.get_context_entity("location") == "المنامة"
    res = memory.resolve_references("ما هو الطقس هناك؟")
    assert "المنامة" in res

    # Device auto-detected from raw text
    memory.update("افتح الشباك", {"intent": "car_control"})
    assert memory.get_context_entity("device_name") == "الشباك"
    res2 = memory.resolve_references("سكره")
    assert "الشباك" in res2


def test_fsm_history_tracking():
    """Verifies turn history contains logged interaction records."""
    memory = FSMMemory()
    memory.update("شغل المكيف", {"intent": "car_control", "entities": {"target": "ac"}})
    memory.update("خليه أبرد", {"intent": "car_control", "entities": {"action": "decrease"}})
    assert len(memory.history) == 2
    assert memory.history[0]["turn"] == 1
    assert memory.history[0]["user_text"] == "شغل المكيف"
    assert memory.history[1]["turn"] == 2
    assert memory.history[1]["user_text"] == "خليه أبرد"


def test_fsm_car_command_preposition_aleeh():
    """Resolves 'قصر عليه' following volume command."""
    memory = FSMMemory()
    memory.update("علي الصوت", {"intent": "car_control", "entities": {"target": "volume"}})
    res = memory.resolve_references("قصر عليه شوية")
    assert "الصوت" in res


def test_fsm_thread_safety():
    """Verifies thread-safety under concurrent access."""
    memory = FSMMemory()
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(50):
                loc = f"City_{worker_id}_{i}"
                memory.update(
                    f"الطقس في {loc}",
                    {"intent": "general_knowledge", "entities": {"location": loc}},
                )
                res = memory.resolve_references("ما هو الوقت هناك؟")
                assert len(res) > 0
                _ = memory.get_last_topic()
                _ = memory.get_context_entity("location")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_fsm_locative_preposition_preservation_min_honak():
    """Verifies 'كم المسافة من هناك؟' preserves preposition 'من' rather than forcing 'في'."""
    memory = FSMMemory()
    memory.update(
        "كم الساعة في مكة؟",
        {"intent": "general_knowledge", "entities": {"location": "مكة"}},
    )
    resolved = memory.resolve_references("كم المسافة من هناك؟")
    assert "من مكة" in resolved
    assert "في مكة" not in resolved

    # Also test "إلى هناك"
    resolved_ila = memory.resolve_references("كيف الطريق إلى هناك؟")
    assert "إلى مكة" in resolved_ila


def test_fsm_locative_wa_honak():
    """Verifies 'وهناك؟' resolves to 'وفي <loc>؟'."""
    memory = FSMMemory()
    memory.update(
        "ما هو الطقس في باريس؟",
        {"intent": "general_knowledge", "entities": {"location": "باريس"}},
    )
    resolved = memory.resolve_references("وهناك؟")
    assert resolved == "وفي باريس؟"


def test_fsm_car_command_fihi_resolves_to_target_not_city():
    """Verifies car command with 'فيه' resolves to car target and prevents city bleeding."""
    memory = FSMMemory()
    # Turn 1: Discuss city
    memory.update(
        "كيف الجو في الرياض؟",
        {"intent": "general_knowledge", "entities": {"location": "الرياض"}},
    )
    assert memory.get_context_entity("location") == "الرياض"

    # Turn 2: Turn on AC
    memory.update(
        "شغل التكييف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
    )
    assert memory.get_context_entity("target") == "ac"

    # Turn 3: "زود فيه" must resolve to car target, NOT previous city "الرياض"
    resolved = memory.resolve_references("زود فيه")
    assert "الرياض" not in resolved
    assert "زود في التكييف" in resolved

    # Also test "قصر فيه"
    resolved_dec = memory.resolve_references("قصر فيه")
    assert "الرياض" not in resolved_dec
    assert "قصر في التكييف" in resolved_dec


def test_fsm_car_command_courtesy_prefix():
    """Verifies courtesy prefix 'لو سمحت خليه أبرد' resolves properly with prefix preserved."""
    memory = FSMMemory()
    memory.update(
        "شغل التكييف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
    )
    resolved = memory.resolve_references("لو سمحت خليه أبرد")
    assert "لو سمحت" in resolved
    assert "التكييف" in resolved
    assert "أبرد" in resolved or "ابرد" in resolved
    assert "خلي التكييف" in resolved

    # Additional courtesy check: "من فضلك سكرها" for window
    memory.update(
        "افتح النافذة",
        {"intent": "car_control", "entities": {"target": "window", "action": "open"}},
    )
    res_courtesy_win = memory.resolve_references("من فضلك سكرها")
    assert "من فضلك" in res_courtesy_win
    assert "النافذة" in res_courtesy_win


def test_fsm_car_positional_term_not_extracted_as_location():
    """Verifies 'شغل التكييف في الخلف' does not set location entity to 'الخلف'."""
    memory = FSMMemory()
    memory.update(
        "شغل التكييف في الخلف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
    )
    assert memory.get_context_entity("location") != "الخلف"
    assert memory.get_context_entity("location") is None

    # Verify when intent_data is None
    memory2 = FSMMemory()
    memory2.update("شغل التكييف في الخلف", None)
    assert memory2.get_context_entity("location") != "الخلف"
    assert memory2.get_context_entity("location") is None

    # Verify when prior location exists, it is not overwritten with "الخلف"
    memory3 = FSMMemory()
    memory3.update(
        "كيف الطقس في الرياض؟",
        {"intent": "general_knowledge", "entities": {"location": "الرياض"}},
    )
    memory3.update(
        "شغل التكييف في الخلف",
        {"intent": "car_control", "entities": {"target": "ac", "action": "turn_on"}},
    )
    assert memory3.get_context_entity("location") == "الرياض"


def test_fsm_implicit_location_does_not_hijack_ac_temperature():
    """Verifies 'كم حرارة التكييف' does not have previous city appended."""
    memory = FSMMemory()
    memory.update(
        "كيف الطقس في دبي؟",
        {"intent": "general_knowledge", "entities": {"location": "دبي"}},
    )
    resolved = memory.resolve_references("كم حرارة التكييف؟")
    assert "دبي" not in resolved
    assert "كم حرارة التكييف؟" == resolved
