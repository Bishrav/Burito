"""CPU-only, held-out synthetic comparison for an intent classifier."""

import json
import re
import resource
import time
from collections import Counter

from academy.classical import (fit_logistic_regression, multiclass_metrics,
                               predict_logistic_probability)


LABELS = ("question", "action_request", "correction", "project_followup", "casual")
TRAIN = {
    "question": ["Why does SQLite use a write lock", "Explain how FTS ranks results",
                 "What does GPU temperature mean", "When should a task ask for approval",
                 "How does Bayes update a prior", "What is the purpose of a context window",
                 "Why did the test report a conflict", "Can you explain matrix multiplication"],
    "action_request": ["Open the project notes", "Find the runtime configuration file",
                       "Run the focused test suite", "Create a synthetic project record",
                       "Launch the local web console", "Read the current status document",
                       "Search the source tree for memory callers", "Show me the model manifest"],
    "correction": ["Actually use the version two schema", "Correction the project is paused",
                   "I meant the local model not the cloud model", "Change that answer to Python three point fourteen",
                   "Replace the old milestone with recovery", "No the task is still pending",
                   "That date is wrong it was November", "Update the preference to concise replies"],
    "project_followup": ["Continue the Atlas project", "Resume where I left off in StudyCircle",
                         "What is my next project task", "Show the latest project milestone",
                         "Where did we stop on the memory work", "Pick up the unfinished Atlas blocker",
                         "Remind me what remains in the project", "Continue from the last checkpoint"],
    "casual": ["Hello Burito", "Hi there", "Thanks that helped", "Good morning",
               "How are you doing", "That is interesting", "Goodbye for now", "Nice work thanks"],
}
TEST = {
    "question": ["How does logistic regression estimate a class", "What caused the mount warning",
                 "Explain why the test was skipped", "When was the last inference run"],
    "action_request": ["Open the roadmap file", "Find the project database helper",
                       "Run the memory retrieval evaluation", "Read the latest architecture notes"],
    "correction": ["Actually the context limit is eight thousand tokens", "Correction my next task is backup verification",
                   "I meant version three not version two", "Change the project state to active"],
    "project_followup": ["Resume the unfinished project work", "What blocker remains for Atlas",
                         "Continue with the next milestone", "Where was the previous checkpoint"],
    "casual": ["Hey Burito", "Thanks for the explanation", "Good evening", "See you later"],
}
RULES = {
    "correction": ("actually", "correction", "meant", "replace", "change"),
    "project_followup": ("continue", "resume", "project", "milestone", "blocker", "checkpoint", "left off"),
    "action_request": ("open", "find", "run", "create", "launch", "read", "search", "show"),
    "question": ("why", "what", "how", "when", "explain", "caused"),
    "casual": ("hello", "hi", "hey", "thanks", "good", "goodbye", "see you"),
}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.casefold())


def _rule(text):
    lowered = text.casefold()
    for label, cues in RULES.items():
        if any(cue in lowered for cue in cues):
            return LABELS.index(label)
    return LABELS.index("casual")


def evaluate():
    train_text = [text for label in LABELS for text in TRAIN[label]]
    train_labels = [LABELS.index(label) for label in LABELS for _ in TRAIN[label]]
    test_text = [text for label in LABELS for text in TEST[label]]
    test_labels = [LABELS.index(label) for label in LABELS for _ in TEST[label]]
    vocabulary = sorted({token for text in train_text for token in _tokens(text)})
    encode = lambda text: [Counter(_tokens(text))[word] for word in vocabulary]
    train_features = [encode(text) for text in train_text]
    test_features = [encode(text) for text in test_text]

    started = time.perf_counter()
    cpu_started = time.process_time()
    models = [fit_logistic_regression(train_features,
                [int(label == class_id) for label in train_labels],
                learning_rate=0.35, steps=1200, l2=0.02)
              for class_id in range(len(LABELS))]
    training_seconds = time.perf_counter() - started
    training_cpu_seconds = time.process_time() - cpu_started
    scores = [predict_logistic_probability(model, test_features) for model in models]
    candidate = [max(range(len(models)), key=lambda index: scores[index][row])
                 for row in range(len(test_text))]
    baseline = [_rule(text) for text in test_text]
    errors = [{"text": text, "expected": LABELS[target], "predicted": LABELS[prediction]}
              for text, target, prediction in zip(test_text, test_labels, candidate)
              if target != prediction]
    return {
        "experiment": "synthetic-intent-classifier-v1",
        "dataset": {"version": "1", "train_examples": len(train_text),
                    "held_out_examples": len(test_text), "classes": list(LABELS),
                    "split": "hand-separated phrase templates; vocabulary fit on training only",
                    "random_seed": "not applicable; deterministic full-batch optimization"},
        "configuration": {"algorithm": "one-vs-rest full-batch logistic regression", "learning_rate": 0.35,
                          "steps": 1200, "l2": 0.02, "feature_encoding": "training-vocabulary unigram counts"},
        "metrics": {"deterministic_rule_baseline": multiclass_metrics(test_labels, baseline),
                    "one_vs_rest_logistic_regression": multiclass_metrics(test_labels, candidate),
                    "training_seconds": training_seconds,
                    "training_cpu_seconds": training_cpu_seconds,
                    "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "cpu_only": True},
        "failure_cases": errors,
        "limitations": [
            "Synthetic English phrases do not represent owner language or real conversation distribution.",
            "The test set is small and hand-authored; metrics are not a production estimate.",
            "No production routing or action policy uses this candidate.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
