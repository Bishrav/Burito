"""Versioned reference lessons. Installation never claims model learning."""

from datetime import datetime, timezone
import json
from pathlib import Path

from .memory import Memory


SEED = Path(__file__).resolve().parent.parent / "curriculum/seed.json"


def catalog(path=SEED):
    lessons = json.loads(Path(path).read_text())["lessons"]
    seen = set()
    for lesson in lessons:
        identifier = lesson["id"]
        if identifier in seen:
            raise ValueError(f"Duplicate lesson: {identifier}")
        # File order is the teaching order: prerequisites must occur first.
        if not set(lesson["prerequisites"]).issubset(seen):
            raise ValueError(f"Missing or unordered prerequisite for {identifier}")
        if not lesson["notes"] or not lesson["sources"] or not lesson["review_prompts"]:
            raise ValueError(f"Incomplete lesson: {identifier}")
        seen.add(identifier)
    return lessons


class School:
    def __init__(self, memory=None):
        self.memory = memory if memory is not None else Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.execute("""CREATE TABLE IF NOT EXISTS knowledge_lessons (
            id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
            lesson_json TEXT NOT NULL, installed_at TEXT NOT NULL
        )""")
        return connection

    def install(self, stage="home"):
        if stage not in {"home", "school", "all"}:
            raise ValueError("Unknown curriculum stage")
        lessons = catalog()
        requested = {item["id"] for item in lessons if stage == "all" or item["stage"] == stage}
        # Install prerequisite closure too, including when starting with school.
        for item in reversed(lessons):
            if item["id"] in requested:
                requested.update(item["prerequisites"])
        connection = self._connect()
        changed = 0
        try:
            with connection:
                for lesson in lessons:
                    if lesson["id"] not in requested:
                        continue
                    serialized = json.dumps(lesson, sort_keys=True)
                    previous = connection.execute(
                        "SELECT revision, lesson_json FROM knowledge_lessons WHERE id = ?",
                        (lesson["id"],),
                    ).fetchone()
                    if previous is not None:
                        if previous["lesson_json"] == serialized:
                            continue
                        if lesson["revision"] <= previous["revision"]:
                            raise ValueError(f"Changed lesson needs a newer revision: {lesson['id']}")
                    connection.execute(
                        """INSERT INTO knowledge_lessons VALUES (?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,
                        lesson_json=excluded.lesson_json, installed_at=excluded.installed_at""",
                        (lesson["id"], lesson["revision"], serialized,
                         datetime.now(timezone.utc).isoformat()),
                    )
                    changed += 1
        finally:
            connection.close()
        return changed

    def installed(self):
        connection = self._connect()
        try:
            return [json.loads(row["lesson_json"]) for row in connection.execute(
                "SELECT lesson_json FROM knowledge_lessons ORDER BY installed_at, id"
            )]
        finally:
            connection.close()
