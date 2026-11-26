"""Run with python3 -m burito from the checkout."""

import argparse
import json
import sqlite3
import sys
import subprocess
from .doctor import report
from .memory import Memory, MEMORY_CATEGORIES, VERIFICATION_STATES
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
from .glossary import Glossary
from .projects import Projects
from .learning import Experiences, SkillProposals
from academy.progress import AcademyProgress, STAGES as ACADEMY_STAGES


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
    glossary = commands.add_parser("glossary", help="Manage owner-confirmed term definitions")
    glossary_commands = glossary.add_subparsers(dest="glossary_command", required=True)
    glossary_define = glossary_commands.add_parser("define", help="Save or update an explicitly confirmed term")
    glossary_define.add_argument("term")
    glossary_define.add_argument("definition")
    glossary_define.add_argument("--source", default="owner")
    glossary_commands.add_parser("list", help="List saved definitions")
    glossary_search = glossary_commands.add_parser("search", help="Find definitions matching a query")
    glossary_search.add_argument("query")
    glossary_forget = glossary_commands.add_parser("forget", help="Remove a saved term")
    glossary_forget.add_argument("id")
    remember = commands.add_parser("remember", help="Store an explicitly provided fact")
    remember.add_argument("content")
    remember.add_argument("--source", default="owner")
    remember.add_argument("--category", choices=sorted(MEMORY_CATEGORIES), default="semantic")
    remember.add_argument("--verification", choices=sorted(VERIFICATION_STATES), default="owner_statement")
    remember.add_argument("--confidence", type=float)
    remember.add_argument("--claim-key", help="Optional owner-defined key for same-claim conflict review")
    commands.add_parser("memories", help="List stored facts as JSON")
    memory_history = commands.add_parser("memory-history", help="Show prior versions of a memory")
    memory_history.add_argument("id")
    memory_conflicts = commands.add_parser("memory-conflicts", help="List unresolved memory conflicts")
    memory_conflicts.add_argument("--all", action="store_true", help="Include resolved and dismissed conflicts")
    resolve_conflict = commands.add_parser("memory-conflict-resolve", help="Resolve or supersede a reviewed conflict")
    resolve_conflict.add_argument("id", type=int)
    resolve_conflict.add_argument("resolution", choices=("resolved", "dismissed", "superseded"))
    resolve_conflict.add_argument("--supersede-memory", help="Memory ID to deactivate when superseding")
    commands.add_parser("teach", help="Teach Burito your basic preferences locally")
    project = commands.add_parser("project", help="Maintain private, owner-controlled project continuity")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_create = project_commands.add_parser("create", help="Create a project record")
    project_create.add_argument("name")
    project_create.add_argument("objective")
    project_list = project_commands.add_parser("list", help="List saved projects")
    project_list.add_argument("--status", choices=("active", "paused", "closed"))
    project_show = project_commands.add_parser("show", help="Show one project")
    project_show.add_argument("id")
    project_update = project_commands.add_parser("update", help="Update project status and next actions")
    project_update.add_argument("id")
    project_update.add_argument("--status", choices=("active", "paused", "closed"))
    project_update.add_argument("--objective")
    project_update.add_argument("--milestone")
    project_update.add_argument("--next-action", action="append")
    project_item = project_commands.add_parser("add-item", help="Add a milestone, task, decision, blocker, or reference")
    project_item.add_argument("id")
    project_item.add_argument("--kind", required=True, choices=("milestone", "task", "decision", "blocker", "reference"))
    project_item.add_argument("--title", required=True)
    project_item.add_argument("--details", default="")
    project_item.add_argument("--status")
    project_item.add_argument("--depends-on", action="append", default=[])
    project_item.add_argument("--evidence")
    project_item.add_argument("--evidence-source")
    project_item.add_argument("--evidence-verification",
        choices=("owner_statement", "direct_observation", "independently_verified"),
        default="owner_statement")
    project_update_item = project_commands.add_parser("update-item", help="Update a project item and attach evidence")
    project_update_item.add_argument("id")
    project_update_item.add_argument("item_id")
    project_update_item.add_argument("--status")
    project_update_item.add_argument("--details")
    project_update_item.add_argument("--evidence")
    project_update_item.add_argument("--evidence-source")
    project_update_item.add_argument("--evidence-verification",
        choices=("owner_statement", "direct_observation", "independently_verified"),
        default="owner_statement")
    project_delete = project_commands.add_parser("delete", help="Delete a project and its correction history")
    project_delete.add_argument("id")
    experience = commands.add_parser("experience", help="Record verified task experience")
    experience_commands = experience.add_subparsers(dest="experience_command", required=True)
    experience_record = experience_commands.add_parser("record", help="Record an attempt and its observed outcome")
    experience_record.add_argument("--objective", required=True)
    experience_record.add_argument("--context", required=True)
    experience_record.add_argument("--approach", required=True)
    experience_record.add_argument("--action", action="append", required=True)
    experience_record.add_argument("--result", action="append", default=[])
    experience_record.add_argument("--error", action="append", default=[])
    experience_record.add_argument("--recovery", action="append", default=[])
    experience_record.add_argument("--lesson", action="append", default=[])
    experience_record.add_argument("--outcome", choices=("attempted", "succeeded", "failed", "inconclusive"), default="attempted")
    experience_record.add_argument("--verification", choices=("unverified", "direct_observation", "independently_verified"), default="unverified")
    experience_record.add_argument("--evidence", action="append", default=[])
    experience_record.add_argument("--evidence-source", action="append", default=[])
    experience_commands.add_parser("list", help="List recorded experiences")
    skill = commands.add_parser("skill", help="Propose and review reusable skills; proposals cannot execute")
    skill_commands = skill.add_subparsers(dest="skill_command", required=True)
    skill_propose = skill_commands.add_parser("propose", help="Propose a skill from verified experiences")
    skill_propose.add_argument("--purpose", required=True)
    skill_propose.add_argument("--experience", action="append", required=True)
    skill_propose.add_argument("--input", action="append", default=[])
    skill_propose.add_argument("--precondition", action="append", required=True)
    skill_propose.add_argument("--tool", action="append", default=[])
    skill_propose.add_argument("--permission", action="append", default=[])
    skill_propose.add_argument("--step", action="append", required=True)
    skill_propose.add_argument("--expected", required=True)
    skill_propose.add_argument("--verification-method", required=True)
    skill_propose.add_argument("--failure", action="append", default=[])
    skill_propose.add_argument("--recovery", action="append", default=[])
    skill_propose.add_argument("--version", type=int, default=1)
    skill_list = skill_commands.add_parser("list", help="List skill proposals")
    skill_review = skill_commands.add_parser("review", help="Accept or reject a proposal without enabling execution")
    skill_review.add_argument("id")
    skill_review.add_argument("decision", choices=("accepted", "rejected"))
    skill_review.add_argument("--note", default="")
    academy = commands.add_parser("academy", help="Track evidence-based private Academy progress")
    academy_commands = academy.add_subparsers(dest="academy_command", required=True)
    academy_record = academy_commands.add_parser("record", help="Record a topic stage and evidence")
    academy_record.add_argument("topic_id")
    academy_record.add_argument("title")
    academy_record.add_argument("--stage", choices=ACADEMY_STAGES, default="planned")
    academy_record.add_argument("--prerequisite", action="append", default=[])
    academy_record.add_argument("--source", action="append", default=[])
    academy_record.add_argument("--source-title", action="append", default=[])
    academy_record.add_argument("--source-license", action="append", default=[])
    academy_record.add_argument("--verify-sources", action="store_true",
                                help="Mark supplied source links as owner-verified; imports remain separate")
    academy_record.add_argument("--evidence", action="append", default=[])
    academy_record.add_argument("--evidence-source", default="owner evaluation")
    academy_commands.add_parser("list", help="List persistent topic progress")
    correct = commands.add_parser("correct", help="Correct an existing owner-provided fact")
    correct.add_argument("id")
    correct.add_argument("content")
    correct.add_argument("--expected", help="Only correct if the current content still matches")
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
                         help="Include saved, owner-maintained project records")
    context.add_argument("--include-suggestions", action="store_true",
                         help="Include recent pending and accepted suggestions with evidence")
    context.add_argument("--include-knowledge", action="store_true",
                         help="Search the local knowledge library for this prompt")
    context.add_argument("--include-experiences", action="store_true",
                         help="Include matching verified task experience records")
    context.add_argument("--include-academy", action="store_true",
                         help="Include persistent Academy progress and evidence")
    context.add_argument("--query", default="", help=argparse.SUPPRESS)
    context.add_argument("--max-chars", type=int, default=12000, help=argparse.SUPPRESS)
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
                              help="Include saved, owner-maintained project records")
    conversation.add_argument("--include-suggestions", action="store_true",
                              help="Include recent pending and accepted suggestions with evidence")
    conversation.add_argument("--include-experiences", action="store_true",
                              help="Include matching task experiences in local context")
    conversation.add_argument("--include-academy", action="store_true",
                              help="Include persistent Academy progress in local context")
    conversation.add_argument("--activity-only", action="store_true",
                              help="Use only activity data; exclude PC inventory, personal facts, and PC tools")
    conversation.add_argument("--enable-online", action="store_true",
                              help="Expose the paid online research tool; each exact query requires approval")
    context.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    conversation.add_argument("--no-system", action="store_true", help="Exclude stored PC inventory")
    conversation.add_argument("--no-files", action="store_true", help="Disable file and application tools")
    conversation.add_argument("--enable-screen-read", action="store_true",
                              help="Enable one-shot local screen OCR; every capture requires approval")
    conversation.add_argument("--enable-desktop-control", action="store_true",
                              help="Enable on-demand KDE window listing and approval-gated focus")
    conversation.add_argument("--enable-browser-search", action="store_true",
                              help="Enable approval-gated exact-query search navigation in Brave Origin")
    conversation.add_argument("--enable-brave-tabs", action="store_true",
                              help="Enable approval-gated tab-count reads from the optional local Brave extension")
    conversation.add_argument("--enable-browser-control", action="store_true",
                              help="Enable approval-gated visible-page reads and basic controls through the local Brave extension")
    web = commands.add_parser("web", help="Start the local-only Burito desktop web console")
    web.add_argument("--model", required=True, help="Installed local model name")
    web.add_argument("--context-tokens", type=int, required=True)
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--notify", action="store_true", help="Show a generic desktop notification for successful replies")
    web.add_argument("--conversation-dir", help="Absolute private transcript directory outside the checkout")
    web.add_argument("--temporary-data", action="store_true", help="Use an isolated temporary lesson database")
    web.add_argument("--lesson", default="home.honesty")
    web.add_argument("--include-project", action="store_true",
                     help="Include saved project records in web chat")
    web.add_argument("--include-personal", action="store_true",
                     help="Include matching explicitly stored personal facts in web chat")
    web.add_argument("--include-experiences", action="store_true",
                     help="Include matching experiences in web chat")
    web.add_argument("--include-academy", action="store_true",
                     help="Include Academy progress and local knowledge in web chat")
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
                                           include_experiences=args.include_experiences,
                                           include_academy=args.include_academy,
                                           knowledge_query=args.query,
                                           max_chars=args.max_chars), indent=2))
        elif args.command == "chat":
            return chat(args.model, args.context_tokens, args.lesson, args.include_personal,
                        include_system=not args.no_system, pc_access=not args.no_files,
                        include_activity=args.include_activity, activity_only=args.activity_only,
                        include_feedback=args.include_feedback, include_project=args.include_project,
                        include_suggestions=args.include_suggestions,
                        include_experiences=args.include_experiences,
                        include_academy=args.include_academy,
                        enable_online=args.enable_online,
                        enable_screen_read=args.enable_screen_read,
                        enable_desktop_control=args.enable_desktop_control,
                        enable_browser_search=args.enable_browser_search,
                        enable_brave_tabs=args.enable_brave_tabs,
                        enable_browser_control=args.enable_browser_control)
        elif args.command == "web":
            from .web import serve
            serve(args.model, args.context_tokens, port=args.port, lesson=args.lesson,
                  include_personal=args.include_personal, include_project=args.include_project,
                  include_experiences=args.include_experiences, include_academy=args.include_academy,
                  include_feedback=args.include_feedback,
                  include_suggestions=args.include_suggestions, include_activity=args.include_activity,
                  temporary_data=args.temporary_data, notify=args.notify, conversation_dir=args.conversation_dir)
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
        elif args.command == "project":
            memory = Memory()
            store = Projects(memory)
            if args.project_command == "create":
                print(json.dumps(store.create(args.name, args.objective), indent=2))
            elif args.project_command == "list":
                print(json.dumps(store.list(args.status), indent=2))
            elif args.project_command == "show":
                project_record = store.get(args.id)
                if project_record is None:
                    print("Project not found", file=sys.stderr)
                    return 1
                print(json.dumps(project_record, indent=2))
            elif args.project_command == "update":
                if not any((args.status, args.objective, args.milestone, args.next_action)):
                    raise ValueError("Specify at least one project field to update")
                print(json.dumps(store.update(args.id, status=args.status,
                    objective=args.objective, current_milestone=args.milestone,
                    next_actions=args.next_action), indent=2))
            elif args.project_command in {"add-item", "update-item"}:
                evidence = None
                if args.evidence is not None or args.evidence_source is not None:
                    if not args.evidence or not args.evidence_source:
                        raise ValueError("Evidence text and evidence source must be supplied together")
                    evidence = [{"text": args.evidence, "source": args.evidence_source,
                                 "verification": args.evidence_verification}]
                if args.project_command == "add-item":
                    print(json.dumps(store.add_item(args.id, args.kind, args.title,
                        details=args.details, status=args.status, evidence=evidence,
                        depends_on=args.depends_on), indent=2))
                else:
                    print(json.dumps(store.update_item(args.id, args.item_id,
                        status=args.status, details=args.details, evidence=evidence), indent=2))
            elif args.project_command == "delete":
                if store.get(args.id) is None or not memory.forget(args.id):
                    print("Project not found", file=sys.stderr)
                    return 1
                print("Project and its revision history deleted")
        elif args.command == "academy":
            progress = AcademyProgress(Memory())
            if args.academy_command == "list":
                print(json.dumps(progress.list(), indent=2))
            else:
                sizes = {len(args.source), len(args.source_title), len(args.source_license)}
                if len(sizes) != 1:
                    raise ValueError("Each source requires one URL, title, and license field")
                sources = [{"url": url, "title": title, "license": license,
                            "verified": args.verify_sources}
                           for url, title, license in zip(args.source, args.source_title,
                                                          args.source_license)]
                print(json.dumps(progress.record(args.topic_id, args.title,
                    prerequisites=args.prerequisite, sources=sources, stage=args.stage,
                    evidence=args.evidence, evidence_source=args.evidence_source), indent=2))
        elif args.command == "experience":
            store = Experiences(Memory())
            if args.experience_command == "record":
                if len(args.evidence) != len(args.evidence_source):
                    raise ValueError("Each evidence entry requires one --evidence-source")
                evidence = [{"text": text, "source": source}
                            for text, source in zip(args.evidence, args.evidence_source)]
                record = store.record(args.objective, args.context, args.approach,
                    attempted_actions=args.action, observed_results=args.result,
                    errors=args.error, recovery_steps=args.recovery,
                    verified_lessons=args.lesson, outcome=args.outcome,
                    verification=args.verification, evidence=evidence)
                print(json.dumps(record, indent=2))
            else:
                print(json.dumps(store.list(), indent=2))
        elif args.command == "skill":
            store = SkillProposals(Memory())
            if args.skill_command == "propose":
                print(json.dumps(store.propose(args.purpose, args.experience,
                    inputs=args.input, preconditions=args.precondition,
                    required_tools=args.tool, permissions=args.permission,
                    procedure=args.step, expected_outcome=args.expected,
                    verification_method=args.verification_method,
                    failure_conditions=args.failure, recovery_strategy=args.recovery,
                    version=args.version), indent=2))
            elif args.skill_command == "list":
                print(json.dumps(store.list(), indent=2))
            elif not store.review(args.id, args.decision, args.note):
                print("Skill proposal not found", file=sys.stderr)
                return 1
            else:
                print("Proposal reviewed; it remains non-executable")
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
            elif args.command == "glossary":
                store = Glossary(memory)
                if args.glossary_command == "define":
                    print(json.dumps(store.define(args.term, args.definition, args.source), indent=2))
                elif args.glossary_command == "list":
                    print(json.dumps(store.list(), indent=2))
                elif args.glossary_command == "search":
                    print(json.dumps(store.search(args.query), indent=2))
                elif args.glossary_command == "forget":
                    if not store.forget(args.id):
                        print("Glossary ID not found", file=sys.stderr)
                        return 1
                    print("Glossary term deleted")
            elif args.command == "remember":
                print(memory.remember(args.content, args.source, args.category, args.confidence,
                                      args.verification, args.claim_key))
            elif args.command == "memories":
                print(json.dumps(memory.list(), indent=2))
            elif args.command == "memory-history":
                print(json.dumps(memory.history(args.id), indent=2))
            elif args.command == "memory-conflicts":
                print(json.dumps(memory.conflicts("all" if args.all else "unresolved"), indent=2))
            elif args.command == "memory-conflict-resolve":
                if not memory.resolve_conflict(args.id, args.resolution, args.supersede_memory):
                    print("Unresolved memory conflict not found", file=sys.stderr)
                    return 1
                print(f"Memory conflict marked {args.resolution}")
            elif args.command == "teach":
                teach(memory)
            elif args.command == "correct":
                if not memory.correct(args.id, args.content, expected_content=args.expected):
                    print("Memory ID not found or its current content changed", file=sys.stderr)
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
