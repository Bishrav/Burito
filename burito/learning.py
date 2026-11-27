"""Evidence-backed experiences and owner-reviewable, non-executable skills."""

import json
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} must contain 1 to {limit} characters")
    return value.strip()


def _items(values, label, maximum=20, item_limit=1000, required=False):
    if not isinstance(values, (list, tuple)) or len(values) > maximum:
        raise ValueError(f"{label} must contain at most {maximum} entries")
    result = [_text(value, label, item_limit) for value in values]
    if required and not result:
        raise ValueError(f"{label} must contain at least one entry")
    return result


def _evidence(values):
    if not isinstance(values, (list, tuple)) or len(values) > 20:
        raise ValueError("Evidence must contain at most 20 records")
    records = []
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("Evidence records require a source and text")
        records.append({
            "source": _text(value.get("source"), "Evidence source", 200),
            "text": _text(value.get("text"), "Evidence text", 1500),
            "observed_at": _text(value.get("observed_at") or _now(), "Evidence timestamp", 64),
        })
    return records


def _store(memory, document, category, source, claim_key=None):
    content = json.dumps(document, ensure_ascii=False, sort_keys=True)
    if len(content) > 19000:
        raise ValueError("Learning record exceeds the 19000-character storage limit")
    verification = document.get("verification", "owner_statement")
    if verification == "unverified":
        verification = "owner_statement"
    return memory.remember(content, source=source, category=category,
                           verification=verification,
                           claim_key=claim_key)


def _documents(memory, category, marker):
    for row in memory.list(category=category):
        try:
            document = json.loads(row["content"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict) and document.get("format") == marker:
            document["id"] = row["id"]
            yield document


class Experiences:
    def __init__(self, memory):
        self.memory = memory

    def record(self, objective, context, approach, *, attempted_actions,
               observed_results=(), errors=(), recovery_steps=(),
               verified_lessons=(), outcome="attempted", evidence=(),
               verification="unverified"):
        if not isinstance(outcome, str) or outcome not in {"attempted", "succeeded", "failed", "inconclusive"}:
            raise ValueError("Outcome must be attempted, succeeded, failed, or inconclusive")
        if not isinstance(verification, str) or verification not in {"unverified", "direct_observation", "independently_verified"}:
            raise ValueError("Unsupported experience verification state")
        checked_evidence = _evidence(evidence)
        results = _items(observed_results, "Observed results")
        lessons = _items(verified_lessons, "Verified lessons")
        if outcome == "succeeded" and (not results or not checked_evidence
                or verification not in {"direct_observation", "independently_verified"}):
            raise ValueError("Success requires observed results, evidence, and verification")
        if lessons and not checked_evidence:
            raise ValueError("Lessons require supporting evidence")
        now = _now()
        document = {
            "format": "burito-experience", "schema": 1,
            "objective": _text(objective, "Objective"),
            "context": _text(context, "Context"),
            "selected_approach": _text(approach, "Approach"),
            "attempted_actions": _items(attempted_actions, "Attempted actions", required=True),
            "observed_results": results,
            "errors": _items(errors, "Errors"),
            "recovery_steps": _items(recovery_steps, "Recovery steps"),
            "verified_lessons": lessons,
            "evidence": checked_evidence,
            "outcome": outcome, "verification": verification,
            "created_at": now,
        }
        identifier = _store(self.memory, document, "experience", "owner-recorded experience")
        document["id"] = identifier
        return document

    def list(self):
        return sorted(_documents(self.memory, "experience", "burito-experience"),
                      key=lambda item: (item["created_at"], item["id"]), reverse=True)

    def get(self, identifier):
        return next((item for item in self.list() if item["id"] == identifier), None)


class SkillProposals:
    """Store proposals only; this module has no execution or permission API."""

    def __init__(self, memory):
        self.memory = memory
        self.experiences = Experiences(memory)

    def propose(self, purpose, experience_ids, *, inputs, preconditions,
                required_tools, permissions, procedure, expected_outcome,
                verification_method, failure_conditions, recovery_strategy,
                version=1):
        if not isinstance(version, int) or version < 1:
            raise ValueError("Skill version must be a positive integer")
        identifiers = list(dict.fromkeys(experience_ids))
        if not identifiers or len(identifiers) > 20:
            raise ValueError("A proposal must cite 1 to 20 experiences")
        evidence = [self.experiences.get(identifier) for identifier in identifiers]
        if any(item is None or item["outcome"] != "succeeded"
               or item["verification"] not in {"direct_observation", "independently_verified"}
               or not item["evidence"] for item in evidence):
            raise ValueError("Skill proposals require verified successful source experiences")
        document = {
            "format": "burito-skill-proposal", "schema": 1,
            "purpose": _text(purpose, "Skill purpose"),
            "inputs": _items(inputs, "Inputs"),
            "preconditions": _items(preconditions, "Preconditions", required=True),
            "required_tools": _items(required_tools, "Required tools", required=True),
            "permissions": _items(permissions, "Permissions", required=True),
            "procedure": _items(procedure, "Procedure", required=True),
            "expected_outcome": _text(expected_outcome, "Expected outcome"),
            "verification_method": _text(verification_method, "Verification method"),
            "failure_conditions": _items(failure_conditions, "Failure conditions", required=True),
            "recovery_strategy": _items(recovery_strategy, "Recovery strategy", required=True),
            "version": version, "source_experiences": identifiers,
            "review_status": "proposed", "verification": "model_inference",
            "validation_status": "proposal_only",
            "evidence_sufficiency": ("single source; repeated evaluation required" if len(identifiers) == 1
                                     else "multiple sources; validation still required"),
            "executable": False,
            "created_at": _now(),
        }
        identifier = _store(self.memory, document, "procedural",
                            "unapproved skill proposal")
        document["id"] = identifier
        return document

    def list(self):
        return sorted(_documents(self.memory, "procedural", "burito-skill-proposal"),
                      key=lambda item: (item["created_at"], item["id"]), reverse=True)

    def review(self, identifier, decision, note=""):
        if not isinstance(decision, str) or decision not in {"accepted", "rejected"}:
            raise ValueError("Review decision must be accepted or rejected")
        row = next((item for item in self.memory.list(category="procedural")
                    if item["id"] == identifier), None)
        proposal = next((item for item in self.list() if item["id"] == identifier), None)
        if row is None or proposal is None:
            return False
        proposal["review_status"] = decision
        proposal["review_note"] = _text(note, "Review note", 500) if note else ""
        proposal["reviewed_at"] = _now()
        proposal["executable"] = False
        return self.memory.correct(identifier,
            json.dumps({key: value for key, value in proposal.items() if key != "id"},
                       ensure_ascii=False, sort_keys=True),
            expected_content=row["content"])
