"""Bounded reference context for the local-only conversation milestone."""

import json

from .memory import Memory
from .school import School


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000):
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
