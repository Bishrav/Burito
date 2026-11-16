"""Bounded reference context for the local-only conversation milestone."""

import json

from .memory import Memory
from .school import School


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000, include_system=True, include_activity=False,
                  activity_only=False, include_feedback=False, include_project=False):
    if activity_only:
        include_personal = False
        include_system = False
        include_activity = True
        include_feedback = False
        include_project = False
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
                "It is not yet surfaced in chat. The next design step is opt-in display of accepted or pending records, "
                "with evidence, before considering recurring suggestions."
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
    return context
