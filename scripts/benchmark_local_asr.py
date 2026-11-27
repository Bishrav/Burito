#!/usr/bin/env python3
"""Evaluate local ASR from an owner-prepared TSV without printing transcript text."""

import argparse
import csv
import json
from pathlib import Path
import re
import resource
import statistics
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from burito.speech import ALLOWED_LANGUAGES, MAX_AUDIO_BYTES, transcribe


def edit_distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for row, left in enumerate(reference, 1):
        current = [row]
        for column, right in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (left != right)))
        previous = current
    return previous[-1]


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def evaluate(manifest):
    rows = []
    with manifest.open(encoding="utf-8", newline="") as stream:
        for line, row in enumerate(csv.reader(stream, delimiter="\t"), 1):
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 3:
                raise ValueError(f"Line {line}: expected path, language, reference columns.")
            name, language, reference = row
            if language not in ALLOWED_LANGUAGES:
                raise ValueError(f"Line {line}: unsupported language selection.")
            audio_path = (manifest.parent / name).resolve()
            if not audio_path.is_file() or audio_path.stat().st_size > MAX_AUDIO_BYTES:
                raise ValueError(f"Line {line}: audio is missing or exceeds the configured limit.")
            with wave.open(str(audio_path), "rb") as audio:
                duration = audio.getnframes() / audio.getframerate()
            if not 0 < duration <= 15:
                raise ValueError(f"Line {line}: expected a WAV clip no longer than 15 seconds.")
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            started = time.perf_counter()
            hypothesis = transcribe(audio_path.read_bytes(), "audio/wav", language)
            elapsed = time.perf_counter() - started
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            words = lambda value: re.findall(r"\w+", value.casefold())
            ref_words, hyp_words = words(reference), words(hypothesis)
            ref_chars = re.sub(r"\s+", "", reference.casefold())
            hyp_chars = re.sub(r"\s+", "", hypothesis.casefold())
            rows.append({
                "language": language,
                "word_errors": edit_distance(ref_words, hyp_words),
                "reference_words": len(ref_words),
                "character_errors": edit_distance(ref_chars, hyp_chars),
                "reference_characters": len(ref_chars),
                "latency_seconds": elapsed,
                "audio_seconds": duration,
                "real_time_factor": elapsed / duration,
                "child_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                "child_peak_rss_mib": after.ru_maxrss / 1024,
            })
    if not rows:
        raise ValueError("The TSV contains no evaluation rows.")

    grouped = {}
    for row in rows:
        grouped.setdefault(row["language"], []).append(row)
    output = {"clips": len(rows), "languages": {}}
    for language, group in grouped.items():
        output["languages"][language] = {
            "clips": len(group),
            "wer": sum(item["word_errors"] for item in group) / max(1, sum(item["reference_words"] for item in group)),
            "cer": sum(item["character_errors"] for item in group) / max(1, sum(item["reference_characters"] for item in group)),
            "median_latency_seconds": statistics.median(item["latency_seconds"] for item in group),
            "p95_latency_seconds": percentile([item["latency_seconds"] for item in group], 0.95),
            "median_real_time_factor": statistics.median(item["real_time_factor"] for item in group),
            "child_cpu_seconds": sum(item["child_cpu_seconds"] for item in group),
            "child_peak_rss_mib": max(item["child_peak_rss_mib"] for item in group),
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="UTF-8 TSV: WAV path, language (en/ne/hi/auto), reference text")
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(args.manifest.resolve()), indent=2, sort_keys=True))
    except (OSError, ValueError, wave.Error, TimeoutError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
