"""Bounded reference context for the local-only conversation milestone."""

import json

from .memory import Memory
from .school import School


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000, include_system=True):
    memory = memory if memory is not None else Memory()
    lessons = {item["id"]: item for item in School(memory).installed()}
    if lesson_id not in lessons:
        raise ValueError("Lesson is not installed; use 'school install' or choose an installed lesson")
    context = {
        "kind": "reference_data",
        "lesson": lessons[lesson_id],
        "personal_memory_included": include_personal,
        "personal_facts": [],
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
    return context
