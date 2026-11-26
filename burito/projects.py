"""Owner-maintained project continuity stored in the private memory database."""

import json
import re
import uuid
from datetime import datetime, timezone


_QUERY_STOP = {"a", "an", "and", "are", "as", "at", "did", "do", "for", "from",
               "have", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or",
               "our", "the", "this", "to", "we", "what", "when", "where", "which",
               "who", "why", "with", "you", "your", "project", "task", "work", "working"}
_CONTINUITY_QUERY = {"blocker", "blockers", "continue", "decision", "decisions", "left",
                     "leave", "last", "milestone", "next", "previous", "progress",
                     "remain", "resume", "stopped", "yesterday"}
_KINDS = {"milestone", "task", "decision", "blocker", "reference"}
_STATUSES = {
    "milestone": {"planned", "in_progress", "completed"},
    "task": {"pending", "in_progress", "blocked", "completed"},
    "decision": {"accepted", "reversed"},
    "blocker": {"open", "resolved"},
    "reference": {"active", "archived"},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} must contain 1 to {limit} characters")
    return value.strip()


class Projects:
    def __init__(self, memory):
        self.memory = memory

    def _records(self):
        result = []
        for row in self.memory.list(category="project"):
            try:
                document = json.loads(row["content"])
            except (TypeError, json.JSONDecodeError):
                continue
            if self._valid(document):
                document["id"] = row["id"]
                document["_provenance"] = {
                    "source": row["source"], "verification": row["verification"],
                    "confidence": row["confidence"],
                }
                result.append(document)
        return result

    @staticmethod
    def _valid(document):
        if (not isinstance(document, dict) or document.get("format") != "burito-project"
                or type(document.get("schema")) is not int or document["schema"] != 1):
            return False
        if (not isinstance(document.get("name"), str)
                or not isinstance(document.get("objective"), str)
                or not isinstance(document.get("current_milestone"), str)
                or not isinstance(document.get("created_at"), str)
                or not isinstance(document.get("updated_at"), str)
                or not isinstance(document.get("status"), str)
                or document.get("status") not in {"active", "paused", "closed"}
                or not isinstance(document.get("next_actions"), list)
                or len(document["next_actions"]) > 20
                or any(not isinstance(action, str) for action in document["next_actions"])
                or not isinstance(document.get("items"), list)
                or len(document["items"]) > 100):
            return False
        item_ids = set()
        for item in document["items"]:
            if (not isinstance(item, dict) or not isinstance(item.get("kind"), str)
                    or item.get("kind") not in _KINDS
                    or not isinstance(item.get("status"), str)
                    or item.get("status") not in _STATUSES[item.get("kind")]
                    or not isinstance(item.get("id"), str)
                    or item["id"] in item_ids or not isinstance(item.get("depends_on"), list)
                    or not isinstance(item.get("evidence"), list)
                    or not isinstance(item.get("title"), str)
                    or not isinstance(item.get("details"), str)
                    or not isinstance(item.get("created_at"), str)
                    or not isinstance(item.get("updated_at"), str)
                    or any(not isinstance(record, dict)
                           or not all(isinstance(record.get(key), str)
                                      for key in ("source", "text", "observed_at", "verification"))
                           for record in item["evidence"])
                    or any(not isinstance(dependency, str) for dependency in item["depends_on"])):
                return False
            item_ids.add(item["id"])
        return all(dependency in item_ids
                   for item in document["items"] for dependency in item["depends_on"])

    def list(self, status=None):
        if status is not None and (not isinstance(status, str)
                                   or status not in {"active", "paused", "closed"}):
            raise ValueError("Project status must be active, paused, or closed")
        return [project for project in sorted(self._records(),
                key=lambda item: (item["updated_at"], item["id"]), reverse=True)
                if status is None or project["status"] == status]

    def get(self, identifier):
        return next((project for project in self._records() if project["id"] == identifier), None)

    def create(self, name, objective):
        name = _text(name, "Project name", 160)
        objective = _text(objective, "Project objective", 2000)
        slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or str(uuid.uuid4())
        if any(project["name"].casefold() == name.casefold() for project in self._records()):
            raise ValueError("A project with this name already exists")
        now = _now()
        document = {
            "format": "burito-project", "schema": 1, "name": name,
            "objective": objective, "status": "active", "current_milestone": "",
            "next_actions": [], "items": [], "created_at": now, "updated_at": now,
        }
        content = json.dumps(document, ensure_ascii=False, sort_keys=True)
        if len(content) > 19000:
            raise ValueError("Project exceeds the 19000-character storage limit")
        identifier = self.memory.remember(
            content,
            source="owner-maintained project", category="project", confidence=1,
            verification="owner_statement", claim_key=f"project:{slug}",
        )
        return self.get(identifier)

    def _save(self, project, updated):
        updated["updated_at"] = _now()
        content = json.dumps({key: value for key, value in updated.items()
                              if key not in {"id", "_provenance"}},
                             ensure_ascii=False, sort_keys=True)
        expected = json.dumps({key: value for key, value in project.items()
                               if key not in {"id", "_provenance"}},
                              ensure_ascii=False, sort_keys=True)
        if len(content) > 19000:
            raise ValueError("Project exceeds the 19000-character storage limit")
        saved = self.memory.correct(project["id"],
            content,
            expected_content=expected)
        if not saved:
            raise ValueError("Project changed during update; reload it and retry")
        return self.get(project["id"])

    def update(self, identifier, *, status=None, objective=None,
               current_milestone=None, next_actions=None):
        project = self.get(identifier)
        if project is None:
            raise ValueError("Project not found")
        updated = dict(project)
        if status is not None:
            if not isinstance(status, str) or status not in {"active", "paused", "closed"}:
                raise ValueError("Project status must be active, paused, or closed")
            updated["status"] = status
        if objective is not None:
            updated["objective"] = _text(objective, "Project objective", 2000)
        if current_milestone is not None:
            updated["current_milestone"] = _text(current_milestone, "Milestone", 300)
        if next_actions is not None:
            if not isinstance(next_actions, (list, tuple)):
                raise ValueError("Next actions must be a list")
            if len(next_actions) > 20:
                raise ValueError("A project can have at most 20 next actions")
            updated["next_actions"] = [_text(action, "Next action", 500) for action in next_actions]
        return self._save(project, updated)

    def add_item(self, identifier, kind, title, *, details="", status=None,
                 evidence=None, depends_on=None):
        project = self.get(identifier)
        if project is None:
            raise ValueError("Project not found")
        if not isinstance(kind, str) or kind not in _KINDS:
            raise ValueError("Unsupported project item kind")
        title = _text(title, "Item title", 300)
        details = details.strip() if isinstance(details, str) else None
        if details is None or len(details) > 4000:
            raise ValueError("Item details must be text up to 4000 characters")
        status = status or {"milestone": "planned", "task": "pending",
                            "decision": "accepted", "blocker": "open",
                            "reference": "active"}[kind]
        if not isinstance(status, str) or status not in _STATUSES[kind]:
            raise ValueError("Status is not valid for this project item")
        item = {
            "id": str(uuid.uuid4()), "kind": kind, "title": title,
            "details": details, "status": status,
            "evidence": self._evidence(evidence or []),
            "depends_on": list(depends_on or []), "created_at": _now(), "updated_at": _now(),
        }
        if len(project["items"]) >= 100:
            raise ValueError("A project can contain at most 100 items")
        if depends_on is not None and (not isinstance(depends_on, (list, tuple)) or len(depends_on) > 20):
            raise ValueError("Task dependencies must be a list of at most 20 item IDs")
        if any(not isinstance(dependency, str) for dependency in item["depends_on"]):
            raise ValueError("Task dependency IDs must be text")
        known = {entry["id"]: entry for entry in project["items"]}
        if kind != "task" and item["depends_on"]:
            raise ValueError("Only tasks can declare dependencies")
        for dependency in item["depends_on"]:
            if dependency not in known or known[dependency]["kind"] != "task":
                raise ValueError("Task dependencies must name existing tasks in this project")
            if status == "completed" and known[dependency]["status"] != "completed":
                raise ValueError("A task cannot complete before its dependencies")
        if status == "completed" and not self._has_verified_evidence(item["evidence"]):
            raise ValueError("A completed item requires directly observed or independently verified evidence")
        updated = dict(project)
        updated["items"] = [*project["items"], item]
        return self._save(project, updated)

    @staticmethod
    def _evidence(evidence):
        if not isinstance(evidence, list) or len(evidence) > 20:
            raise ValueError("Evidence must be a list of at most 20 records")
        checked = []
        for entry in evidence:
            if not isinstance(entry, dict):
                raise ValueError("Evidence records must be objects")
            source = _text(entry.get("source"), "Evidence source", 200)
            text = _text(entry.get("text"), "Evidence text", 1000)
            observed_at = entry.get("observed_at") or _now()
            verification = entry.get("verification", "owner_statement")
            if (not isinstance(verification, str) or verification not in
                    {"owner_statement", "direct_observation", "independently_verified"}):
                raise ValueError("Unsupported project evidence verification state")
            checked.append({"source": source, "text": text,
                            "observed_at": _text(observed_at, "Evidence timestamp", 64),
                            "verification": verification})
        return checked

    @staticmethod
    def _has_verified_evidence(evidence):
        return any(item["verification"] in {"direct_observation", "independently_verified"}
                   for item in evidence)

    def update_item(self, identifier, item_id, *, status=None, details=None,
                    evidence=None):
        project = self.get(identifier)
        if project is None:
            raise ValueError("Project not found")
        updated = dict(project)
        updated["items"] = [dict(item) for item in project["items"]]
        item = next((entry for entry in updated["items"] if entry["id"] == item_id), None)
        if item is None:
            raise ValueError("Project item not found")
        if status is not None:
            if not isinstance(status, str) or status not in _STATUSES[item["kind"]]:
                raise ValueError("Status is not valid for this project item")
            item["status"] = status
        if details is not None:
            if not isinstance(details, str) or len(details) > 4000:
                raise ValueError("Item details must be text up to 4000 characters")
            item["details"] = details.strip()
        if evidence is not None:
            item["evidence"] = self._evidence(evidence)
        if item["status"] == "completed" and not self._has_verified_evidence(item["evidence"]):
            raise ValueError("A completed item requires directly observed or independently verified evidence")
        if item["status"] == "completed":
            by_id = {entry["id"]: entry for entry in updated["items"]}
            if any(by_id[dependency]["status"] != "completed" for dependency in item["depends_on"]):
                raise ValueError("A task cannot complete before its dependencies")
        elif any(entry["kind"] == "task" and entry["status"] == "completed"
                 and item_id in entry["depends_on"] for entry in updated["items"]):
            raise ValueError("A dependency cannot be reopened while dependent tasks are completed")
        item["updated_at"] = _now()
        return self._save(project, updated)

    def context(self, query="", limit=3):
        summaries = []
        projects = self.list("active")
        terms = {word for word in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE)
                 if len(word) > 1 and word not in _QUERY_STOP}
        if terms:
            ranked = []
            for project in projects:
                fields = [project["name"], project["objective"],
                          project["current_milestone"], *project["next_actions"]]
                fields.extend(item["title"] + " " + item["details"]
                              for item in project["items"])
                words = set(re.findall(r"[^\W_]+", " ".join(fields).casefold(),
                                       flags=re.UNICODE))
                score = len(terms & words)
                if score:
                    ranked.append((score, project))
            ranked.sort(key=lambda pair: (pair[0], pair[1]["updated_at"], pair[1]["id"]),
                        reverse=True)
            projects = [project for _, project in ranked]
            if not projects and terms & _CONTINUITY_QUERY:
                projects = self.list("active")
        for project in projects[:max(1, min(int(limit), 3))]:
            summaries.append({
                key: project[key] for key in
                ("id", "name", "objective", "current_milestone", "next_actions")
            } | {"status": project["status"], "provenance": project["_provenance"], "items": [
                {**{key: item[key] for key in ("id", "kind", "title", "status", "evidence", "depends_on")},
                 "details": item["details"][:600]}
                for item in project["items"] if item["status"] not in {"completed", "resolved", "archived", "reversed"}
            ][:8], "completed_tasks": [
                {"id": item["id"], "title": item["title"], "evidence": item["evidence"][:1],
                 "updated_at": item["updated_at"]}
                for item in project["items"] if item["kind"] == "task" and item["status"] == "completed"
            ][-3:]})
        return summaries
