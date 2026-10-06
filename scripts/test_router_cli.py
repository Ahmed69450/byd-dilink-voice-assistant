#!/usr/bin/env python3
"""
Interactive CLI Simulation & Diagnostic Tool for BYD DiLink Voice Assistant Router.

Supports:
- --query "النص": One-off execution of an Arabic utterance.
- --demo: Automated multi-turn conversational driving scenario demonstration.
- --interactive: Interactive REPL simulation driving mode.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure UTF-8 I/O encoding across terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure Python modules under android/app/src/main/python can be imported
python_dir = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "main" / "python"
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))

from router import VoiceAssistantRouter


def format_output_card(result: Dict[str, Any], router: VoiceAssistantRouter) -> None:
    """Formats and prints pipeline execution results and FSM state clearly."""
    raw = result.get("raw_input", "")
    resolved = result.get("resolved_input", "")
    intent = result.get("intent", "unknown")
    status = result.get("status", "unknown")
    spoken = result.get("spoken_response", "")
    car_action = result.get("car_action")

    fsm_topic = router.memory.get_last_topic()
    entities = router.memory.entities
    turn = router.memory.turn_count

    print("-" * 65)
    print(f"[Input]    : {raw}")
    if resolved and resolved != raw:
        print(f"[Resolved] : {resolved}")
    print(f"[Intent]   : {intent} (Status: {status})")

    if car_action:
        cmd = car_action.get("command", "")
        params = car_action.get("parameters", {})
        print(f"[CarAction]: Command={cmd} | Params={json.dumps(params, ensure_ascii=False)}")

    print(f"[Spoken]   : {spoken}")
    print(
        f"[FSM State]: Turn={turn} | Intent={fsm_topic.get('intent')} | "
        f"Location={entities.get('location')} | Target={entities.get('target')}"
    )
    print("-" * 65)


def run_demo(router: VoiceAssistantRouter) -> None:
    """Runs a multi-turn driving simulation covering all 4 core scenarios."""
    scenarios = [
        # Scenario 1: AC Control & Adjustment Continuity
        ("السيناريو 1: التحكم بالتكييف وتعديل الحرارة تتابعياً", [
            "شغل المكيف على 22",
            "خليه أبرد",
        ]),
        # Scenario 2: Weather & Time Location Continuity
        ("السيناريو 2: الطقس والوقت مع حل إشارة المكان (هناك)", [
            "كم الساعة في مكة المكرمة؟",
            "وكيف الطقس هناك؟",
        ]),
        # Scenario 3: Chitchat & Vehicle Persona
        ("السيناريو 3: السوالف والتحايا وهوية السيارة", [
            "مرحبا، صباح الخير",
            "مين انت؟",
        ]),
        # Scenario 4: Media & Audio Controls
        ("السيناريو 4: الوسائط والتحكم بالصوت", [
            "شغل موسيقى هادية",
            "علي الصوت شوي",
        ]),
    ]

    print("\n========================================================")
    print("    BYD DiLink Voice Assistant - Multi-Turn Demo Mode")
    print("========================================================\n")

    for title, turns in scenarios:
        print(f"\n[Scenario] {title}\n")
        for utterance in turns:
            res = router.process(utterance)
            format_output_card(res, router)

    print("\n[Done] انتهت جولة العرض التوضيحي بنجاح!\n")


def run_interactive(router: VoiceAssistantRouter) -> None:
    """Runs interactive driving simulation shell."""
    print("\n========================================================")
    print("    BYD DiLink Voice Assistant - Interactive Shell")
    print("    اكتب أمرك الصوتي بالعربية (أو 'exit'/'خروج' للإنهاء)")
    print("    اكتب 'reset' لتصفير ذاكرة السياق FSM Memory")
    print("========================================================\n")

    while True:
        try:
            user_input = input("[Driver]: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "خروج", "إنهاء"]:
                print("مع السلامة ورافقتك السلامة في رحلتك!")
                break

            if user_input.lower() in ["reset", "تصفير", "مسح"]:
                router.reset_memory()
                print("[Reset] تم تصفير ذاكرة السياق FSM Memory بنجاح.\n")
                continue

            result = router.process(user_input)
            format_output_card(result, router)

        except (KeyboardInterrupt, EOFError):
            print("\nتم إنهاء المحاكاة.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BYD DiLink Voice Assistant Master Router Test & CLI Simulation Tool"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="One-off query utterance to execute through the pipeline."
    )
    parser.add_argument(
        "--demo", "-d",
        action="store_true",
        help="Run the automated multi-turn scenario demonstration."
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive conversational driving simulation session."
    )

    args = parser.parse_args()
    router = VoiceAssistantRouter()

    if args.query:
        result = router.process(args.query)
        format_output_card(result, router)
    elif args.demo:
        run_demo(router)
    elif args.interactive:
        run_interactive(router)
    else:
        # Default behavior if no arguments provided: show demo
        run_demo(router)


if __name__ == "__main__":
    main()
