"""Evidence-based Academy progress stored in Burito's private memory database."""

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit


STAGES = (
    "planned", "sources_verified", "material_registered", "material_retrieved",
    "exercise_passed", "algorithm_implemented", "experiment_reproduced",
    "capability_benchmarked", "production_approved",
)
_ORDER = {stage: index for index, stage in enumerate(STAGES)}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, label, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} must contain 1 to {limit} characters")
    return value.strip()


class AcademyProgress:
    def __init__(self, memory):
        self.memory = memory

    def list(self):
        result = []
        for row in self.memory.list(category="research"):
            try:
                record = json.loads(row["content"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(record, dict) and record.get("format") == "burito-academy-progress":
                record["id"] = row["id"]
                record["provenance"] = {"source": row["source"],
                                        "verification": row["verification"]}
                result.append(record)
        return sorted(result, key=lambda item: item["topic_id"])

    def get(self, topic_id):
        return next((item for item in self.list() if item["topic_id"] == topic_id), None)

    def record(self, topic_id, title, *, prerequisites=(), sources=(), stage="planned",
               evidence=(), evidence_source="owner evaluation"):
        topic_id = _text(topic_id, "Topic ID", 80).casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", topic_id):
            raise ValueError("Topic ID may contain only letters, numbers, dot, underscore, and hyphen")
        title = _text(title, "Topic title", 200)
        if not isinstance(stage, str) or stage not in _ORDER:
            raise ValueError("Unsupported Academy progress stage")
        existing = self.get(topic_id)
        if existing and existing["title"] != title:
            raise ValueError("Topic title conflicts with the existing topic record")
        prerequisites = [_text(value, "Prerequisite", 100) for value in prerequisites]
        if len(prerequisites) > 30:
            raise ValueError("A topic can have at most 30 prerequisites")
        if not isinstance(sources, (list, tuple)) or len(sources) > 30:
            raise ValueError("A topic can have at most 30 source references")
        if not sources and existing:
            sources = existing["sources"]
        checked_sources = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("Source references must be objects")
            url = _text(source.get("url"), "Source URL", 1000)
            parsed_url = urlsplit(url)
            if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username:
                raise ValueError("Academy references must use HTTPS URLs")
            if not isinstance(source.get("verified", False), bool):
                raise ValueError("Source verification must be an explicit boolean")
            checked_sources.append({
                "url": url,
                "title": _text(source.get("title"), "Source title", 300),
                "license": _text(source.get("license"), "Source license", 300),
                "verified": bool(source.get("verified", False)),
            })
        if _ORDER[stage] >= _ORDER["sources_verified"]:
            if not checked_sources or any(not source["verified"] for source in checked_sources):
                raise ValueError("This stage requires registered, verified sources")
        if stage in {"exercise_passed", "algorithm_implemented", "experiment_reproduced",
                     "capability_benchmarked", "production_approved"} and not evidence:
            raise ValueError("This stage requires evaluation evidence")
        if not isinstance(evidence, (list, tuple)) or len(evidence) > 20:
            raise ValueError("Evidence must contain at most 20 records")
        checked_evidence = [{"source": _text(evidence_source, "Evidence source", 200),
                             "result": _text(value, "Evidence", 1000), "recorded_at": _now()}
                            for value in evidence]
        if existing:
            if sources:
                checked_sources = list({source["url"]: source for source in
                                        [*existing["sources"], *checked_sources]}.values())
            else:
                checked_sources = existing["sources"]
            if prerequisites:
                prerequisites = list(dict.fromkeys([*existing["prerequisites"], *prerequisites]))
            else:
                prerequisites = existing["prerequisites"]
            events = list(existing["events"])
            current_stage = max(existing["current_stage"], stage, key=_ORDER.get)
            new_stage = current_stage
            row = next(item for item in self.memory.list(category="research")
                       if item["id"] == existing["id"])
        else:
            events = []
            new_stage = stage
            row = None
        events.append({"stage": stage, "evidence": checked_evidence, "recorded_at": _now()})
        if len(events) > 100:
            raise ValueError("Academy topic history is limited to 100 events")
        document = {
            "format": "burito-academy-progress", "schema": 1,
            "topic_id": topic_id, "title": title,
            "prerequisites": list(dict.fromkeys(prerequisites)),
            "sources": checked_sources, "current_stage": new_stage,
            "events": events, "updated_at": _now(),
        }
        content = json.dumps(document, ensure_ascii=False, sort_keys=True)
        if len(content) > 18000:
            raise ValueError("Academy progress record exceeds its storage limit")
        if row is None:
            identifier = self.memory.remember(content, source="Academy progress registry",
                category="research", verification="owner_statement",
                claim_key=f"academy-topic:{topic_id}")
        else:
            if not self.memory.correct(row["id"], content, expected_content=row["content"]):
                raise ValueError("Academy progress changed during update; reload and retry")
            identifier = row["id"]
        return self.get(topic_id)
