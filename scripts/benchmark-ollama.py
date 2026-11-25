"""Measure local Ollama context, throughput, host memory and GPU memory."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import threading
from urllib.request import ProxyHandler, Request, build_opener

ENDPOINT = "http://127.0.0.1:11434"
HTTP = build_opener(ProxyHandler({}))


def api(path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(ENDPOINT + path, data=body, headers={"Content-Type": "application/json"})
    with HTTP.open(request, timeout=600) as response:
        return json.load(response)


def memory_sample():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, value = line.split(":", 1)
        if name in {"MemTotal", "MemAvailable"}:
            fields[name] = int(value.split()[0]) // 1024
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL, timeout=3,
        )
        vram = [int(line) for line in result.splitlines()]
    except (OSError, ValueError, subprocess.SubprocessError):
        vram = []
    return fields["MemTotal"] - fields["MemAvailable"], vram


def benchmark(model, context, runs):
    def generate(prompt, limit):
        return api("/api/generate", {
            "model": model, "prompt": prompt, "stream": False, "think": False,
            "keep_alive": "5m",
            "options": {"num_ctx": context, "num_predict": limit, "temperature": 0, "seed": 42},
        })

    api("/api/generate", {"model": model, "keep_alive": 0})
    baseline_ram, baseline_vram = memory_sample()
    samples = [(baseline_ram, baseline_vram)]
    stop = threading.Event()

    def sample():
        while not stop.wait(0.25):
            samples.append(memory_sample())

    sampler = threading.Thread(target=sample)
    sampler.start()
    try:
        cold = generate("Reply with the word ready.", 8)
        rates = []
        for _ in range(runs):
            reply = generate("Write a numbered list of 50 different everyday objects.", 128)
            rates.append(reply["eval_count"] * 1e9 / reply["eval_duration"])
        marker = "maple"
        # The repeated common words tokenize to roughly one token each.
        filler = " blue green yellow orange" * ((context - 512) // 4)
        reply = generate(f"Remember the code word {marker}. Ignore the filler.{filler}\n"
                         "What was the code word? Answer with the word only.", 32)
        loaded = api("/api/ps")["models"]
        placement = next(entry for entry in loaded if entry["name"] == model)
        samples.append(memory_sample())
    finally:
        stop.set()
        sampler.join()
        api("/api/generate", {"model": model, "keep_alive": 0})

    return {
        "requested_context": context,
        "allocated_context": placement.get("context_length"),
        "long_prompt_tokens": reply["prompt_eval_count"],
        "recall_response": reply["response"].strip(),
        "recall_passed": reply["response"].strip().casefold().rstrip(".") == marker,
        "cold_load_seconds": round(cold["load_duration"] / 1e9, 2),
        "generation_tokens_per_second_median": round(statistics.median(rates), 1),
        "host_ram_used_baseline_mib": baseline_ram,
        "host_ram_used_sampled_peak_mib": max(ram for ram, _ in samples),
        "gpu_vram_used_baseline_mib": baseline_vram,
        "gpu_vram_used_sampled_peak_mib": [
            max(vram[index] for _, vram in samples if len(vram) > index)
            for index in range(len(baseline_vram))
        ],
        "ollama_model_bytes": placement["size"],
        "ollama_vram_bytes": placement["size_vram"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="burito-local:latest")
    parser.add_argument("--contexts", type=int, nargs="+", default=[4096, 8192, 16384])
    args = parser.parse_args()
    if any(context < 1024 for context in args.contexts):
        parser.error("context lengths must be at least 1024")
    print(json.dumps({"ollama": api("/api/version")["version"], "model": args.model}), flush=True)
    for context in args.contexts:
        print(json.dumps(benchmark(args.model, context, runs=3)), flush=True)


if __name__ == "__main__":
    main()
