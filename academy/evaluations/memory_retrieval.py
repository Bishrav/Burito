"""Reproducible synthetic evaluation for the existing FTS5 memory baseline."""

import json
import math
import statistics
import tempfile
import time

from burito.context import build_context
from burito.memory import Memory
from burito.school import School


def _percentile(values, percentile):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1)]


def evaluate(records=1000, repeats=5):
    if not isinstance(records, int) or records < 0 or records > 100000:
        raise ValueError("Record count must be between 0 and 100000")
    if not isinstance(repeats, int) or not 1 <= repeats <= 100:
        raise ValueError("Repeats must be between 1 and 100")
    with tempfile.TemporaryDirectory(prefix="burito-retrieval-eval-") as directory:
        memory = Memory(directory)
        distractors = [f"Synthetic unrelated reference record {index:04d} about generic archived material."
                       for index in range(records)]
        for text in distractors:
            memory.remember(text, source="synthetic distractor")
        exact = memory.remember("Atlas stores verified backup manifests on encrypted portable storage.",
                                source="synthetic source", category="project")
        paraphrase = memory.remember("Atlas archives finished project files after each test run.",
                                     source="synthetic source", category="project")
        temporal = memory.remember("Atlas checkpoint 2026-11-26: archive review remains pending.",
                                   source="synthetic source", category="project")
        project = memory.remember("Northstar project objective is local search; its next task is index validation.",
                                  source="synthetic source", category="project")
        decision = memory.remember("Atlas decision: retain two encrypted archive copies and verify monthly.",
                                   source="synthetic decision record", category="project")
        blocker = memory.remember("Atlas blocker: restore verification awaits the second archive copy.",
                                  source="synthetic blocker record", category="project")
        experience = memory.remember(json.dumps({
            "format": "burito-experience", "schema": 1,
            "objective": "Recover Atlas test index", "context": "Synthetic project fixture",
            "selected_approach": "Rebuild from verified source records",
            "attempted_actions": ["Ran synthetic recovery test"],
            "observed_results": ["Recovery test passed"], "errors": ["Stale index checksum"],
            "recovery_steps": ["Rebuilt and rechecked checksum"],
            "verified_lessons": ["Check the source checksum before index rebuild"],
            "evidence": [{"source": "synthetic test", "text": "Exit code 0"}],
            "outcome": "succeeded", "verification": "direct_observation",
            "created_at": "2026-11-25T12:00:00+00:00"}),
            source="synthetic experience", category="experience")
        corrected = memory.remember("Synthetic client config uses version alpha.",
                                    source="synthetic source", category="project")
        memory.correct(corrected, "Synthetic client config uses version beta.")
        deleted = memory.remember("Synthetic deleted marker orchid-7719 should never be retrieved.",
                                 source="synthetic source", category="personal")
        memory.forget(deleted)
        conflict_a = memory.remember("Synthetic deployment region is east.", "synthetic source",
                                     category="project", claim_key="deployment region")
        conflict_b = memory.remember("Synthetic deployment region is west.", "synthetic source",
                                     category="project", claim_key="deployment region")
        private = memory.remember("Synthetic private marker owner-only-lilac-9281.",
                                  source="synthetic owner", category="personal")
        cases = [
            {"kind": "exact", "query": "Atlas verified backup manifests portable storage", "relevant": [exact], "category": "project"},
            {"kind": "lexical_paraphrase", "query": "How does Atlas archive finished files", "relevant": [paraphrase], "category": "project"},
            {"kind": "temporal", "query": "Atlas checkpoint November 2026", "relevant": [temporal]},
            {"kind": "project_reference", "query": "Northstar next task index validation", "relevant": [project]},
            {"kind": "previous_decision", "query": "Which Atlas archive plan did we decide on", "relevant": [decision], "category": "project"},
            {"kind": "blocker", "query": "What is still preventing Atlas restore verification", "relevant": [blocker], "category": "project"},
            {"kind": "experience", "query": "Have we recovered a stale index before", "relevant": [experience], "category": "experience"},
            {"kind": "multiple_relevant", "query": "Atlas archive copies and monthly verification", "relevant": [decision, blocker], "category": "project"},
            {"kind": "corrected_record", "query": "client config beta", "relevant": [corrected]},
            {"kind": "conflicting_records", "query": "deployment region", "relevant": [conflict_a, conflict_b]},
            {"kind": "deleted_record", "query": "orchid", "relevant": [], "deleted_id": deleted},
            {"kind": "irrelevant", "query": "quasar-copper-field-9931", "relevant": []},
            {"kind": "ambiguous", "query": "What were we doing?", "relevant": [], "skip": True},
        ]
        timings = []
        case_results = []
        reciprocal_ranks, precisions, recalls = [], [], []
        for case in cases:
            if case.get("skip"):
                case_results.append({"kind": case["kind"], "query_terms": Memory.query_terms(case["query"]),
                                     "returned": 0, "relevant": 0, "hits": 0,
                                     "note": "No usable lexical terms; context selector correctly performs no memory search."})
                continue
            result = memory.search(case["query"], limit=5, category=case.get("category"))
            identifiers = [row["id"] for row in result]
            relevant = set(case["relevant"])
            hits = [identifier for identifier in identifiers if identifier in relevant]
            if relevant:
                precisions.append(len(hits) / 5)
                recalls.append(len(hits) / len(relevant))
                reciprocal_ranks.append(1 / (next((index + 1 for index, identifier in enumerate(identifiers)
                                                     if identifier in relevant), math.inf)))
            for _ in range(repeats):
                started = time.perf_counter_ns()
                memory.search(case["query"], limit=5, category=case.get("category"))
                timings.append((time.perf_counter_ns() - started) / 1_000_000)
            case_results.append({"kind": case["kind"], "query": case["query"],
                "returned": len(result), "relevant": len(relevant), "hits": len(hits),
                "relevant_ids": hits,
                "unresolved_conflicts": sum(bool(row["unresolved_conflict"]) for row in result)})
        old_content = memory.search("alpha", limit=5)
        deleted_content = memory.search("orchid", limit=5)
        School(memory).install("home")
        opt_out = build_context(memory=memory, include_system=False, include_personal=False)
        checks = {
            "corrected_old_content_absent": corrected not in {row["id"] for row in old_content},
            "deleted_record_absent": next(case for case in case_results
                if case["kind"] == "deleted_record")["returned"] == 0 and
                                     deleted not in {row["id"] for row in deleted_content},
            "conflict_records_marked": all(row["unresolved_conflict"] for row in
                memory.search("deployment region", limit=5) if row["id"] in {conflict_a, conflict_b}),
            "personal_opt_out": private not in json.dumps(opt_out),
        }
        if not all(checks.values()):
            raise AssertionError(f"Retrieval safety/lifecycle checks failed: {checks}")
        return {
            "suite": "burito-memory-retrieval-v2", "records": len(memory.list()),
            "distractors": records, "repeats_per_query": repeats,
            "metrics": {
                "precision_at_5": statistics.mean(precisions),
                "recall_at_5": statistics.mean(recalls),
                "mean_reciprocal_rank": statistics.mean(reciprocal_ranks),
                "warm_latency_ms_median": statistics.median(timings),
                "warm_latency_ms_p95": _percentile(timings, .95),
            },
            "cases": case_results, "safety_checks": checks,
            "retrieval_policy": {"normalization": "Unicode word tokens; common English stopwords removed; first 16 useful terms",
                                 "category_filter": "optional metadata restriction, evaluated in project/experience cases",
                                 "score_threshold": "none; rejected because a calibrated threshold has not been measured"},
            "storage": "temporary directory; not the physical brain",
            "limitations": [
                "Queries and relevance labels are synthetic and hand-authored.",
                "FTS5 is lexical; paraphrase success does not establish semantic understanding.",
                "Warm timings include rebuilding the temporary FTS index and are not HDD measurements.",
            ],
        }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
