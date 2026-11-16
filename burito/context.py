"""Bounded reference context for the local-only conversation milestone."""

import json

from .memory import Memory
from .school import School


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000, include_system=True, include_activity=False,
                  activity_only=False, include_feedback=False):
    if activity_only:
        include_personal = False
        include_system = False
        include_activity = True
        include_feedback = False
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
    return context
