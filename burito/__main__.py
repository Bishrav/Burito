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
from . import activity
from .access import dispatch
from .feedback import Feedback, RATINGS
from .suggestions import Suggestions, EVIDENCE_SOURCES, REVIEW_STATES
from .knowledge import Knowledge


def main(argv=None):
    parser = argparse.ArgumentParser(description="Burito foundation: diagnostics and local memory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Read-only readiness report; no network calls")
    commands.add_parser("init", help="Create private local memory storage")
    knowledge = commands.add_parser("knowledge", help="Manage Burito's local searchable reference library")
    knowledge_commands = knowledge.add_subparsers(dest="knowledge_command", required=True)
    knowledge_add = knowledge_commands.add_parser("add", help="Index an owner-selected text or Markdown file")
    knowledge_add.add_argument("path")
    knowledge_commands.add_parser("list", help="List imported library documents")
    knowledge_search = knowledge_commands.add_parser("search", help="Search imported documents")
    knowledge_search.add_argument("query")
    knowledge_search.add_argument("--limit", type=int, default=5)
    knowledge_forget = knowledge_commands.add_parser("forget", help="Remove one imported document and its index")
    knowledge_forget.add_argument("id")
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
    feedback = commands.add_parser("feedback", help="Store explicit private feedback for future chats")
    feedback_commands = feedback.add_subparsers(dest="feedback_command", required=True)
    feedback_add = feedback_commands.add_parser("add", help="Record your rating and correction or note")
    feedback_add.add_argument("rating", choices=RATINGS)
    feedback_add.add_argument("note")
    feedback_commands.add_parser("list", help="List owner-provided feedback records")
    feedback_forget = feedback_commands.add_parser("forget", help="Delete one feedback record by ID")
    feedback_forget.add_argument("id")
    suggestions = commands.add_parser("suggestions", help="Record and review evidence-backed suggestions locally")
    suggestions_commands = suggestions.add_subparsers(dest="suggestions_command", required=True)
    suggestion_add = suggestions_commands.add_parser("add", help="Record a suggestion and its evidence")
    suggestion_add.add_argument("content")
    suggestion_add.add_argument("--evidence-source", required=True, choices=EVIDENCE_SOURCES)
    suggestion_add.add_argument("--evidence", required=True)
    suggestion_add.add_argument("--reference", default="",
                                help="Optional local event ID, date, or other provenance reference")
    suggestion_list = suggestions_commands.add_parser("list", help="List reviewed suggestions")
    suggestion_list.add_argument("--status", choices=REVIEW_STATES)
    suggestion_review = suggestions_commands.add_parser("review", help="Accept or dismiss a suggestion")
    suggestion_review.add_argument("id")
    suggestion_review.add_argument("status", choices=REVIEW_STATES)
    suggestion_review.add_argument("--note", default="")
    suggestion_forget = suggestions_commands.add_parser("forget", help="Delete a suggestion and its evidence")
    suggestion_forget.add_argument("id")
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
    context.add_argument("--include-activity", action="store_true",
                         help="Include a bounded local 7-day foreground-app summary")
    context.add_argument("--include-feedback", action="store_true",
                         help="Include explicit owner feedback in this context")
    context.add_argument("--include-project", action="store_true",
                         help="Include the curated Burito repository map and current milestone")
    context.add_argument("--include-suggestions", action="store_true",
                         help="Include recent pending and accepted suggestions with evidence")
    context.add_argument("--include-knowledge", action="store_true",
                         help="Search the local knowledge library for this prompt")
    context.add_argument("--query", default="", help=argparse.SUPPRESS)
    context.add_argument("--activity-only", action="store_true",
                         help="Preview only activity data; exclude PC inventory and personal facts")
    conversation = commands.add_parser("chat", help="Start local eve chat after runtime and model setup")
    conversation.add_argument("--model", required=True, help="Name of an installed local model")
    conversation.add_argument("--context-tokens", type=int, required=True,
                              help="Context size actually configured on the local model server")
    conversation.add_argument("--lesson", default="home.honesty")
    conversation.add_argument("--include-personal", action="store_true")
    conversation.add_argument("--include-activity", action="store_true",
                              help="Include a bounded local 7-day foreground-app summary")
    conversation.add_argument("--include-feedback", action="store_true",
                              help="Include explicit owner feedback in this chat")
    conversation.add_argument("--include-project", action="store_true",
                              help="Include a curated Burito repository map and current milestone")
    conversation.add_argument("--include-suggestions", action="store_true",
                              help="Include recent pending and accepted suggestions with evidence")
    conversation.add_argument("--activity-only", action="store_true",
                              help="Use only activity data; exclude PC inventory, personal facts, and PC tools")
    context.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    conversation.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    conversation.add_argument("--no-files", action="store_true", help="Disable file and application tools")
    web = commands.add_parser("web", help="Start the local-only Burito desktop web console")
    web.add_argument("--model", required=True, help="Installed local model name")
    web.add_argument("--context-tokens", type=int, required=True)
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--lesson", default="home.honesty")
    web.add_argument("--include-project", action="store_true")
    web.add_argument("--include-feedback", action="store_true")
    web.add_argument("--include-suggestions", action="store_true")
    web.add_argument("--include-activity", action="store_true")
    commands.add_parser("access-bridge", help=argparse.SUPPRESS)
    pc = commands.add_parser("pc", help="Local computer inventory and metadata changes")
    pc_commands = pc.add_subparsers(dest="pc_command", required=True)
    for name in ("scan", "status", "changes", "enable", "pause", "monitor-status"):
        pc_commands.add_parser(name)
    activity_parser = commands.add_parser("activity", help="Opt-in local foreground-app tracking")
    activity_commands = activity_parser.add_subparsers(dest="activity_command", required=True)
    for name in ("enable", "pause", "status", "report", "clear", "labels"):
        activity_subcommand = activity_commands.add_parser(name)
        if name == "report":
            activity_subcommand.add_argument("--days", type=int, default=7)
    activity_label = activity_commands.add_parser("label", help="Save app context with its source")
    activity_label.add_argument("app_id")
    activity_label.add_argument("context_note")
    activity_label.add_argument("--source", choices=("owner_confirmed", "assistant_app_role"),
                                default="owner_confirmed")
    activity_unlabel = activity_commands.add_parser("unlabel", help="Remove your context for an app ID")
    activity_unlabel.add_argument("app_id")
    activity_commands.add_parser("collect", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(report(), indent=2))
        elif args.command == "access-bridge":
            raw = sys.stdin.read(20001)
            if len(raw) > 20000:
                raise ValueError('PC access request is too large')
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError('Expected a PC access request object')
            print(json.dumps(dispatch(request)))
        elif args.command == "context":
            print(json.dumps(build_context(args.lesson, args.include_personal,
                                           include_system=not args.no_system,
                                           include_activity=args.include_activity,
                                           activity_only=args.activity_only,
                                           include_feedback=args.include_feedback,
                                           include_project=args.include_project,
                                           include_suggestions=args.include_suggestions,
                                           include_knowledge=args.include_knowledge,
                                           knowledge_query=args.query), indent=2))
        elif args.command == "chat":
            return chat(args.model, args.context_tokens, args.lesson, args.include_personal,
                        include_system=not args.no_system, pc_access=not args.no_files,
                        include_activity=args.include_activity, activity_only=args.activity_only,
                        include_feedback=args.include_feedback, include_project=args.include_project,
                        include_suggestions=args.include_suggestions)
        elif args.command == "web":
            from .web import serve
            serve(args.model, args.context_tokens, port=args.port, lesson=args.lesson,
                  include_project=args.include_project, include_feedback=args.include_feedback,
                  include_suggestions=args.include_suggestions, include_activity=args.include_activity)
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
        elif args.command == "activity":
            if args.activity_command == "collect":
                activity.collect()
            elif args.activity_command == "enable":
                print(activity.enable())
            elif args.activity_command == "pause":
                print(activity.pause())
            elif args.activity_command == "status":
                print(json.dumps(activity.status(), indent=2))
            elif args.activity_command == "report":
                print(json.dumps(activity.report(args.days), indent=2))
            elif args.activity_command == "labels":
                print(json.dumps(activity.labels(), indent=2))
            elif args.activity_command == "label":
                print(json.dumps(activity.label(args.app_id, args.context_note, source=args.source), indent=2))
            elif args.activity_command == "unlabel":
                if not activity.unlabel(args.app_id):
                    print("Application label not found", file=sys.stderr)
                    return 1
                print("Application label removed")
            elif args.activity_command == "clear":
                print(json.dumps(activity.clear(), indent=2))
        elif args.command == "feedback":
            feedback_store = Feedback()
            if args.feedback_command == "add":
                identifier = feedback_store.add(args.rating, args.note)
                print(json.dumps({"id": identifier, "rating": args.rating,
                                  "stored": True, "source": "owner_provided"}, indent=2))
            elif args.feedback_command == "list":
                print(json.dumps(feedback_store.list(), indent=2))
            elif args.feedback_command == "forget":
                if not feedback_store.forget(args.id):
                    print("Feedback ID not found", file=sys.stderr)
                    return 1
                print("Feedback deleted from the live database")
        elif args.command == "suggestions":
            store = Suggestions()
            if args.suggestions_command == "add":
                result = store.add(args.content, args.evidence_source, args.evidence, args.reference)
                print(json.dumps(result, indent=2))
            elif args.suggestions_command == "list":
                print(json.dumps(store.list(args.status), indent=2))
            elif args.suggestions_command == "review":
                if not store.review(args.id, args.status, args.note):
                    print("Suggestion ID not found", file=sys.stderr)
                    return 1
                print(f"Suggestion marked {args.status}")
            elif args.suggestions_command == "forget":
                if not store.forget(args.id):
                    print("Suggestion ID not found", file=sys.stderr)
                    return 1
                print("Suggestion and its evidence deleted from the live database")
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
            elif args.command == "knowledge":
                library = Knowledge(memory)
                if args.knowledge_command == "add":
                    print(json.dumps(library.add(args.path), indent=2))
                elif args.knowledge_command == "list":
                    print(json.dumps(library.list(), indent=2))
                elif args.knowledge_command == "search":
                    print(json.dumps(library.search(args.query, args.limit), indent=2))
                elif args.knowledge_command == "forget":
                    if not library.forget(args.id):
                        print("Knowledge document ID not found", file=sys.stderr)
                        return 1
                    print("Document and its searchable chunks removed")
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
