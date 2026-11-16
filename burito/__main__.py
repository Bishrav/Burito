"""Run with python3 -m burito from the checkout."""

import argparse
import json
import sqlite3
import sys
import subprocess
from .doctor import report
from .memory import Memory
from .education import teach
from .school import School, catalog
from .context import build_context
from .chat import chat
from .awareness import Awareness, enable, pause, monitor_status
from . import activity
from .access import dispatch
from .feedback import Feedback, RATINGS
from .suggestions import Suggestions, EVIDENCE_SOURCES, REVIEW_STATES


def main(argv=None):
    parser = argparse.ArgumentParser(description="Burito foundation: diagnostics and local memory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Read-only readiness report; no network calls")
    commands.add_parser("init", help="Create private local memory storage")
    remember = commands.add_parser("remember", help="Store an explicitly provided fact")
    remember.add_argument("content")
    remember.add_argument("--source", default="owner")
    commands.add_parser("memories", help="List stored facts as JSON")
    commands.add_parser("teach", help="Teach Burito your basic preferences locally")
    correct = commands.add_pars…3568 tokens truncated…:
                if not memory.correct(args.id, args.content):
                    print("Memory ID not found", file=sys.stderr)
                    return 1
                print("Memory corrected")
            elif args.command == "backup":
                print(f"Private backup created: {memory.backup(args.destination)}")
            elif args.command == "forget":
                if not memory.forget(args.id):
                    print("Memory ID not found", file=sys.stderr)
                    return 1
                print("Memory deleted from the live database")
    except (ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        print(f"Burito: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
