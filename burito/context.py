"""Bounded reference context for the local-only conversation milestone."""

import json
import re
from pathlib import Path

from .memory import Memory
from .school import School


_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(password|passwd|passphrase|secret|api[\s_-]?key|access[\s_-]?token|token)"
    r"(\s*(?:is|[:=])\s*|\s+)([^\s,;.!?]{8,})"
)


def _redact_context(value):
    """Mask obvious credential-like values before untrusted text reaches the model."""
    if isinstance(value, str):
        return _SENSITIVE_VALUE.sub(lambda match: match.group(1) + match.group(2) + "[REDACTED]", value)
    if isinstance(value, list):
        return [_redact_context(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_context(item) for key, item in value.items()}
    return value


def build_context(lesson_id="home.honesty", include_personal=False, memory=None,
                  max_chars=12000, include_system=True, include_activity=False,
                  activity_only=False, include_feedback=False, include_project=False,
                  include_suggestions=False, include_knowledge=False, knowledge_query="",
                  include_experiences=False, include_academy=False):
    if activity_only:
        include_personal = False
        include_system = False
        include_activity = True
        include_feedback = False
        include_project = False
        include_suggestions = False
        include_knowledge = False
        include_experiences = False
        include_academy = False
    memory = memory if memory is not None else Memory()
    search_query = " ".join(Memory.query_terms(knowledge_query)[:16])
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
        "experience_context_included": False,
        "academy_context_included": False,
        "suggestions_included": include_suggestions,
        "knowledge_included": include_knowledge,
        "experience_records": [],
        "academy_progress": [],
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
        query = search_query
        allowed_categories = ("semantic", "personal", "preference")
        if query:
            facts = memory.search(query, limit=10, categories=allowed_categories)
        else:
            facts = [record for record in memory.list()
                     if record["category"] in allowed_categories]
        selected_facts = facts[-10:]
        for record in selected_facts:
            selected = {key: record[key] for key in
                        ("id", "content", "source", "category", "verification",
                         "confidence", "unresolved_conflict")}
            context["personal_facts"].append(selected)
            if len(json.dumps(context)) > max_chars:
                context["personal_facts"].pop()
                context["truncated"] = True
                break
        if len(selected_facts) > len(context["personal_facts"]):
            context["truncated"] = True
        # Owner-defined meanings are private and follow the same opt-in as
        # personal facts. Keep retrieval focused on the current user turn.
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
        from .projects import Projects
        context["remembered_projects"] = []
        for project in Projects(memory).context(knowledge_query):
            context["remembered_projects"].append(project)
            if len(json.dumps(context)) > max_chars:
                context["remembered_projects"].pop()
                context["truncated"] = True
                break
        if not context["remembered_projects"]:
            context.pop("remembered_projects")
            context["project_context_included"] = False
    if include_experiences and search_query:
        rows = memory.search(search_query, limit=3, category="experience")
        for row in rows:
            try:
                record = json.loads(row["content"])
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(record, dict) or record.get("format") != "burito-experience":
                continue
            context["experience_records"].append({
                "id": row["id"], "source": row["source"],
                **{key: record.get(key) for key in (
                    "objective", "context", "selected_approach", "outcome",
                    "verification", "observed_results", "errors", "recovery_steps",
                    "verified_lessons", "evidence", "created_at")},
            })
            if len(json.dumps(context)) > max_chars:
                context["experience_records"].pop()
                context["truncated"] = True
                break
        context["experience_context_included"] = bool(context["experience_records"])
    if include_academy:
        from academy.progress import AcademyProgress
        records = AcademyProgress(memory).list()
        terms = {term for term in search_query.casefold().split() if len(term) > 2}
        ranked = sorted(records, key=lambda record: (
            sum(term in (record["topic_id"] + " " + record["title"]).casefold()
                for term in terms), record["updated_at"]), reverse=True)
        for record in ranked[:6]:
            selected = {key: record[key] for key in (
                "topic_id", "title", "prerequisites", "sources", "current_stage", "events",
                "provenance")}
            selected["events"] = selected["events"][-3:]
            context["academy_progress"].append(selected)
            if len(json.dumps(context)) > max_chars:
                context["academy_progress"].pop()
                context["truncated"] = True
                break
        context["academy_context_included"] = bool(context["academy_progress"])
        if not context["academy_progress"]:
            context.pop("academy_progress")
        curriculum_path = Path(__file__).resolve().parent.parent / "academy/curriculum/core.json"
        try:
            topics = json.loads(curriculum_path.read_text(encoding="utf-8"))["topics"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            topics = []
        progress_by_id = {record["topic_id"]: record["current_stage"] for record in records}
        context["academy_topics"] = [{
            key: topic[key] for key in ("id", "title", "objectives", "implementation",
                                       "exercise", "completion", "sources") if key in topic
        } | {"recorded_stage": progress_by_id.get(topic.get("id"), "not_recorded")
              if isinstance(topic.get("id"), str) else "not_recorded"}
            for topic in topics[:12] if isinstance(topic, dict)]
        if len(json.dumps(context)) > max_chars:
            context["academy_topics"] = context["academy_topics"][:4]
            context["truncated"] = True
        if len(json.dumps(context)) > max_chars:
            context.pop("academy_topics")
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
    if include_knowledge and search_query:
        from .knowledge import Knowledge
        matches = Knowledge(memory).search(search_query, limit=5)
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
    return _redact_context(context)
