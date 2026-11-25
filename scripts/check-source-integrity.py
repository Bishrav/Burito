"""Validate tracked and new, non-ignored source files before installing dependencies."""
import ast
import json
from pathlib import Path
import subprocess
import sys

TEXT_SUFFIXES = {
    ".css", ".desktop", ".html", ".js", ".json", ".md", ".mjs", ".py", ".service",
    ".sh", ".svg", ".timer", ".toml", ".ts", ".txt", ".yaml", ".yml",
}
TEXT_NAMES = {".gitignore", ".gitattributes", "Modelfile"}
STRIP_TYPES = """
const fs = require('node:fs');
const { stripTypeScriptTypes } = require('node:module');
process.stdout.write(stripTypeScriptTypes(fs.readFileSync(0, 'utf8')));
"""


def run_syntax(command, source):
    result = subprocess.run(command, input=source, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip())


def check(path):
    source = path.read_text(encoding="utf-8")
    if "\0" in source:
        raise ValueError("NUL byte in text")

    match path.suffix:
        case ".py":
            ast.parse(source, filename=str(path))
        case ".json":
            json.loads(source)
        case ".sh":
            run_syntax(["bash", "-n"], source)
        case ".ts":
            result = subprocess.run(
                ["node", "--no-warnings", "-e", STRIP_TYPES],
                input=source, text=True, capture_output=True,
            )
            if result.returncode:
                raise ValueError(result.stderr.strip())
            run_syntax(["node", "--input-type=module", "--check"], result.stdout)
        case ".js" | ".mjs":
            run_syntax(["node", "--input-type=module", "--check"], source)


def main():
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    failures = 0
    checked = 0
    for name in sorted(set(names.decode("utf-8").split("\0")) - {""}):
        path = Path(name)
        if path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue
        checked += 1
        try:
            check(path)
        except (OSError, UnicodeError, ValueError, SyntaxError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            failures += 1
    print(f"Checked {checked} source files, {failures} failed.")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
