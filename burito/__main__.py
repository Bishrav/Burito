"""Run with python3 -m burito from the checkout."""

import argparse
import json
import sqlite3
import sys
import subprocess
from .doctor import report
from .memory import Memory
from .education import teach
from .school import School, catalog
from .context import build_context
from .chat import chat
from .awareness import Awareness, enable, pause, monitor_status


def main(argv=None):
    parser = argparse.ArgumentParser(description="Burito foundation: diagnostics and local memory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Read-only readiness report; no network calls")
    commands.add_parser("init", help="Create private local memory storage")
    remember = commands.add_parser("remember", help="Store an explicitly provided fact")
    remember.add_argument("content")
    remember.add_argument("--source", default="owner")
    commands.add_parser("memories", help="List stored facts as JSON")
    commands.add_parser("teach", help="Teach Burito your basic preferences locally")
    correct = commands.add_parser("correct", help="Correct an existing owner-provided fact")
    correct.add_argument("id")
    correct.add_argument("content")
    backup = commands.add_parser("backup", help="Create a consistent private database backup")
    backup.add_argument("destination", help="Absolute path to a new file in an existing directory")
    forget = commands.add_parser("forget", help="Delete one fact by its full ID")
    forget.add_argument("id")
    school = commands.add_parser("school", help="General curriculum, separate from personal facts")
    school_commands = school.add_subparsers(dest="school_command", required=True)
    school_commands.add_parser("list", help="List available lessons in teaching order")
    lesson = school_commands.add_parser("lesson", help="Read a reference lesson and review prompts")
    lesson.add_argument("id")
    install = school_commands.add_parser("install", help="Store selected lessons locally; not model training")
    install.add_argument("--stage", choices=["home", "school", "all"], default="home")
    school_commands.add_parser("status", help="List installed references; does not assess understanding")
    context = commands.add_parser("context", help="Preview one installed lesson for local AI context")
    context.add_argument("--lesson", default="home.honesty")
    context.add_argument("--include-personal", action="store_true")
    conversation = commands.add_parser("chat", help="Start local eve chat after runtime and model setup")
    conversation.add_argument("--model", required=True, help="Name of an installed local model")
    conversation.add_argument("--context-tokens", type=int, required=True,
                              help="Context size actually configured on the local model server")
    conversation.add_argument("--lesson", default="home.honesty")
    conversation.add_argument("--include-personal", action="store_true")
    context.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    conversation.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    pc = commands.add_parser("pc", help="Local computer inventory and metadata changes")
    pc_commands = pc.add_subparsers(dest="pc_command", required=True)
    for name in ("scan", "status", "changes", "enable", "pause", "monitor-status"):
        pc_commands.add_parser(name)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(report(), indent=2))
        elif args.command == "context":
            print(json.dumps(build_context(args.lesson, args.include_personal, include_system=not args.no_system), indent=2))
        elif args.command == "chat":
            return chat(args.model, args.context_tokens, args.lesson, args.include_personal,
                        include_system=not args.no_system)
        elif args.command == "pc":
            if args.pc_command == "enable":
                print(enable())
            elif args.pc_command == "pause":
                print(pause())
            elif args.pc_command == "monitor-status":
                print(json.dumps(monitor_status(), indent=2))
            else:
                awareness = Awareness()
                result = awareness.scan() if args.pc_command == "scan" else awareness.summary() if args.pc_command == "status" else awareness.changes()
                print(json.dumps(result, indent=2))
        elif args.command == "school":
            if args.school_command == "list":
                for lesson in catalog():
                    print(f"{lesson['id']} [{lesson['stage']}; {lesson['subject']}] {lesson['title']}")
            elif args.school_command == "lesson":
                lessons = {lesson["id"]: lesson for lesson in catalog()}
                if args.id not in lessons:
                    raise ValueError("Unknown lesson ID; use 'school list'")
                print(json.dumps(lessons[args.id], indent=2))
            elif args.school_command == "install":
                print(f"Stored {School().install(args.stage)} new or updated reference lesson(s). Not model training.")
            else:
                lessons = School().installed()
                print(json.dumps({"reference_lessons": len(lessons), "understanding_assessed": False,
                                  "installed_ids": [lesson["id"] for lesson in lessons]}, indent=2))
        else:
            memory = Memory()
            if args.command == "init":
                print(f"Local memory ready: {memory.initialize()}")
            elif args.command == "remember":
                print(memory.remember(args.content, args.source))
            elif args.command == "memories":
                print(json.dumps(memory.list(), indent=2))
            elif args.command == "teach":
                teach(memory)
            elif args.command == "correct":
                if not memory.correct(args.id, args.content):
                    print("Memory ID not found", file=sys.stderr)
                    return 1
                print("Memory corrected")
            elif args.command == "backup":
                print(f"Private backup created: {memory.backup(args.destination)}")
            elif args.command == "forget":
                if not memory.forget(args.id):
                    print("Memory ID not found", file=sys.stderr)
                    return 1
                print("Memory deleted from the live database")
    except (ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        print(f"Burito: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
