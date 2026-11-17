"""Bounded reference context for the local-only conversation milestone."""

import json

from .memory import Memory
from .school import School


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000, include_system=True, include_activity=False,
                  activity_only=False, include_feedback=False, include_project=False,
                  include_suggestions=False, include_knowledge=False, knowledge_query=""):
    if activity_only:
        include_personal = False
        include_system = False
        include_activity = True
        include_feedback = False
        include_project = False
        include_suggestions = False
        include_knowledge = False
    memory = memory if memory is not None else Memory()
    lessons = {item["id"]: item for item in School(memory).installed()}
    if lesson_id not in lessons:
        raise ValueError("Lesson is not installed; use 'school install' or choose an installed lesson")
    context = {
        "kind": "reference_data",
        "lesson": lessons[lesson_id],
        "personal_memory_included": include_personal,
        "personal_facts": [],
        "owner_feedback_included": include_feedback,
        "project_context_included": include_project,
        "suggestions_included": include_suggestions,
        "knowledge_included": include_knowledge,
        "activity_included": include_activity,
        "activity_only": activity_only,
        "understanding_assessed": False,
        "truncated": False,
    }
    if len(json.dumps(context)) > max_chars:
        raise ValueError("Selected lesson exceeds the context size limit")
    if include_system:
        from .awareness import Awareness
        summary = Awareness(memory).summary()
        context["pc_inventory"] = summary
        if len(json.dumps(context)) > max_chars:
            # Keep the source timestamp and uncertainty even when trimming details.
            context["pc_inventory"] = {key: summary[key] for key in
                                       ("available", "last_scan", "scope") if key in summary}
            context["pc_inventory"]["partial_categories"] = list(summary.get("partial_or_unavailable", {}))
            context["pc_inventory"]["details_omitted"] = True
            context["truncated"] = True
        if len(json.dumps(context)) > max_chars:
            context.pop("pc_inventory")
    if include_activity:
        from .activity import report as activity_report
        report = activity_report(days=7, memory=memory)
        context["activity_observations"] = {
            "period_days": report["period_days"],
            "event_count": report["event_count"],
            "last_observed": report["last_observed"],
            "applications": report["foreground_estimates"][:5],
            "interpretation": report["interpretation"],
            "scope": report["scope"],
        }
        if len(json.dumps(context)) > max_chars:
            context["activity_observations"]["applications"] = report["foreground_estimates"][:3]
            context["activity_observations"]["details_omitted"] = True
            context["truncated"] = True
        if len(json.dumps(context)) > max_chars:
            context.pop("activity_observations")
            raise ValueError("Activity summary exceeds the local context size limit")
    if include_personal:
        facts = memory.list()
        for record in facts[-10:]:
            selected = {key: record[key] for key in ("id", "content", "source")}
            context["personal_facts"].append(selected)
            if len(json.dumps(context)) > max_chars:
                context["personal_facts"].pop()
                context["truncated"] = True
                break
        if len(facts) > len(context["personal_facts"]):
            context["truncated"] = True
        # Owner-defined meanings are private and follow the same opt-in as
        # personal facts. Keep retrieval focused on the current user turn.
        query = knowledge_query.strip()
        if query:
            from .glossary import Glossary
            matches = Glossary(memory).search(query, limit=5)
            if matches:
                context["glossary_matches"] = [
                    {"term": item["term"], "definition": item["definition"],
                     "source": item["source"]}
                    for item in matches
                ]
                if len(json.dumps(context)) > max_chars:
                    context.pop("glossary_matches")
                    context["truncated"] = True
    if include_feedback:
        from .feedback import Feedback
        records = Feedback(memory).list(limit=10)
        context["owner_feedback"] = [
            {key: record[key] for key in ("rating", "note", "created_at")}
            for record in reversed(records)
        ]
        if len(json.dumps(context)) > max_chars:
            context.pop("owner_feedback")
            context["owner_feedback_included"] = False
            context["truncated"] = True
    if include_project:
        context["project_context"] = {
            "repository": "Burito",
            "verified_paths": {
                "burito/__main__.py": "Python command-line interface",
                "burito/context.py": "Bounded local chat context builder",
                "burito/suggestions.py": "Private evidence-backed suggestion records and duplicate checks",
                "runtime/agent/instructions.md": "Persistent local assistant instructions",
                "runtime/agent/instructions/lesson.ts": "Per-session local context bridge",
                "docs/ROADMAP.md": "Project stages and longer-term design",
                "docs/STATUS.md": "Implemented features and current next steps",
            },
            "current_milestone": (
                "The owner-reviewed suggestion store now supports evidence, review states, and exact normalized duplicates. "
                "Ordinary chats can opt in to recent pending and accepted records with evidence. "
                "The next step is owner verification and review of duplicate and evidence handling."
            ),
            "limits": (
                "Only the listed paths and their stated roles are verified in this context. "
                "Do not invent other repository paths, commands, implementations, or claim to have inspected their contents. "
                "This context grants no file or action access."
            ),
        }
        if len(json.dumps(context)) > max_chars:
            context.pop("project_context")
            context["project_context_included"] = False
            context["truncated"] = True
    if include_suggestions:
        from .suggestions import Suggestions
        records = Suggestions(memory).active(limit=5)
        context["owner_suggestions"] = []
        context["suggestions_included"] = True
        if len(json.dumps(context)) > max_chars:
            context.pop("owner_suggestions")
            context["suggestions_included"] = False
            context["truncated"] = True
        for record in records if context["suggestions_included"] else []:
            selected = {
                "id": record["id"], "content": record["content"],
                "status": record["status"], "review_note": record["review_note"][:300],
                "evidence": [
                    {"source": item["source"], "detail": item["detail"][:500],
                     "reference": item["reference"][:160], "added_at": item["added_at"]}
                    for item in record["evidence"][-3:]
                ],
            }
            context["owner_suggestions"].append(selected)
            if len(json.dumps(context)) > max_chars:
                context["owner_suggestions"].pop()
                context["truncated"] = True
                break
        if len(records) > len(context.get("owner_suggestions", [])):
            context["truncated"] = True
        if records and not context.get("owner_suggestions") and context["suggestions_included"]:
            context.pop("owner_suggestions", None)
            context["suggestions_included"] = False
    if include_knowledge and knowledge_query.strip():
        from .knowledge import Knowledge
        matches = Knowledge(memory).search(knowledge_query, limit=5)
        passages = []
        for match in matches:
            passages.append({"source": match["source_path"], "title": match["title"],
                             "excerpt": match["content"][:1800]})
        context["knowledge_matches"] = passages
        if len(json.dumps(context)) > max_chars:
            context["knowledge_matches"] = passages[:2]
            context["truncated"] = True
        if len(json.dumps(context)) > max_chars:
            context.pop("knowledge_matches", None)
            context["knowledge_included"] = False
            context["truncated"] = True
    return context
