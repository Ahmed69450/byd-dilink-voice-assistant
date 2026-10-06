"""
Master Intent Router for BYD DiLink Voice Assistant.

Coordinates:
- Speech text normalization (NLU)
- Conversational state tracking & coreference resolution (FSM Memory)
- Intent classification across Car Control, General Knowledge, and Chitchat
- Safe dispatch to Branch A (Car Control), Branch B (REST APIs), or Branch C (Chitchat)
- Chaquopy Android bridge entry point (process_voice_input)
"""

import json
from typing import Any, Dict, Optional

from nlu_classifier import classify_intent, normalize_arabic
from fsm_memory import FSMMemory
from chitchat_engine import ChitchatEngine
from api_clients import handle_general_knowledge
from car_commands import map_entities_to_car_action


class VoiceAssistantRouter:
    """
    Unified Voice Assistant Router coordinating NLU, FSM Memory,
    Car Commands, Knowledge APIs, and Chitchat Engine.
    """

    def __init__(
        self,
        chitchat_path: Optional[str] = None,
        session_timeout: float = 300.0,
        api_config: Optional[Dict[str, Any]] = None,
    ):
        self.chitchat = ChitchatEngine(data_path=chitchat_path)
        self.memory = FSMMemory(session_timeout_seconds=session_timeout)
        self.api_config: Dict[str, Any] = api_config or {}

    def reset_memory(self) -> None:
        """Resets conversational memory and context state."""
        self.memory.reset()

    def _classify_with_memory(self, resolved_text: str, raw_text: str) -> Dict[str, Any]:
        """
        Classifies user intent on context-resolved text and enriches
        entities with conversational memory context.
        """
        nlu_res = classify_intent(resolved_text)
        intent = nlu_res.get("intent", "chitchat")
        entities = nlu_res.get("entities") or {}

        # Retain prior context entities if missing in current utterance
        if intent == "car_control":
            if not entities.get("target"):
                context_target = self.memory.get_context_entity("target")
                if context_target:
                    entities["target"] = context_target
        elif intent == "general_knowledge":
            if not entities.get("location"):
                context_loc = self.memory.get_context_entity("location")
                if context_loc:
                    entities["location"] = context_loc

        nlu_res["entities"] = entities
        return nlu_res

    def process(self, raw_text: str) -> Dict[str, Any]:
        """
        Processes a raw Arabic user utterance through the full pipeline:
        Listen -> Context Resolution -> Classification -> Branch Execution -> Memory Update.

        Guarantees structured dict response:
        {
            "status": "success" | "error",
            "intent": "car_control" | "chitchat" | "general_knowledge",
            "raw_input": str,
            "resolved_input": str,
            "spoken_response": str,
            "car_action": dict | None,
            "error": None | str
        }
        """
        try:
            raw_text = raw_text or ""
            clean_text = raw_text.strip()

            # Handle empty / silence inputs gracefully
            if not clean_text:
                return {
                    "status": "success",
                    "intent": "chitchat",
                    "raw_input": raw_text,
                    "resolved_input": "",
                    "spoken_response": "أهلاً بك! أنا في الاستماع، كيف يمكنني مساعدتك؟",
                    "car_action": None,
                    "error": None,
                }

            # 1. Resolve multi-turn conversational references & pronouns
            resolved_text = self.memory.resolve_references(clean_text)

            # 2. Intent Classification & Entity Extraction
            nlu_res = self._classify_with_memory(resolved_text, clean_text)
            intent = nlu_res.get("intent", "chitchat")
            entities = nlu_res.get("entities") or {}

            car_action: Optional[Dict[str, Any]] = None
            spoken_response: str = ""

            # 3. Branch Dispatch
            if intent == "car_control":
                car_action, spoken_response = map_entities_to_car_action(entities, resolved_text)
            elif intent == "general_knowledge":
                spoken_response = handle_general_knowledge(
                    query=resolved_text,
                    entities=entities,
                    config=self.api_config,
                )
            else:  # chitchat
                intent = "chitchat"
                response = self.chitchat.get_response(resolved_text)
                if response:
                    spoken_response = response
                else:
                    spoken_response = "أنا رفيقك الصوتي في سيارة BYD DiLink. كيف يمكنني مساعدتك اليوم؟"

            # 4. Update FSM Context Memory
            self.memory.update(
                user_text=clean_text,
                intent_data={"intent": intent, "entities": entities},
                response_data={"spoken_response": spoken_response, "car_action": car_action},
            )

            # 5. Return structured result
            return {
                "status": "success",
                "intent": intent,
                "raw_input": raw_text,
                "resolved_input": resolved_text,
                "spoken_response": spoken_response,
                "car_action": car_action,
                "error": None,
            }

        except Exception as exc:
            return {
                "status": "error",
                "intent": "chitchat",
                "raw_input": raw_text,
                "resolved_input": raw_text,
                "spoken_response": "عذراً، حدث خطأ غير متوقع أثناء معالجة طلبك.",
                "car_action": None,
                "error": str(exc),
            }


# =====================================================================
# Top-level Chaquopy Android Bridge Entry Point
# =====================================================================

_GLOBAL_ROUTER: Optional[VoiceAssistantRouter] = None


def get_router(config: Optional[Dict[str, Any]] = None) -> VoiceAssistantRouter:
    """Returns or initializes the singleton VoiceAssistantRouter instance."""
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = VoiceAssistantRouter(api_config=config)
    elif config:
        _GLOBAL_ROUTER.api_config.update(config)
    return _GLOBAL_ROUTER


def process_voice_input(raw_text: str, config_json: str = "{}") -> str:
    """
    Top-level entry point called from Android Kotlin (Chaquopy bridge).
    Accepts raw user speech text and optional JSON config, returns
    serialized JSON result string.
    """
    config: Dict[str, Any] = {}
    if config_json:
        try:
            parsed = json.loads(config_json)
            if isinstance(parsed, dict):
                config = parsed
        except Exception:
            config = {}

    router = get_router(config)
    result = router.process(raw_text)
    return json.dumps(result, ensure_ascii=False)
