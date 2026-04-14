"""
Profiler example — simulated LLM pipeline with nested steps.

Run with:
    PROFILER_ENABLED=true python scripts/example_profiler.py

Without the env var, the script runs normally but no profiling output
is produced (NullProfiler is active).
"""

import random
import time

from core_utils.logger import configure_logger
from core_utils.profiler import profiler

configure_logger(level="INFO", console=True, log_file="logs/example.log")

# Session context — appears in every report header and JSON export
profiler.set_context(pipeline="demo_pipeline", env="local")


# ── Simulated pipeline functions ──────────────────────────────────────────────


def load_dataset(name: str) -> list[dict[str, str]]:
    time.sleep(0.05 + random.uniform(0, 0.03))
    return [{"id": str(i), "text": f"record {i} from {name}"} for i in range(6)]


def embed_text(text: str) -> list[float]:
    time.sleep(0.01 + random.uniform(0, 0.005))
    return [random.random() for _ in range(8)]


def call_llm(prompt: str, model: str) -> str:
    time.sleep(0.2 + random.uniform(0, 0.1))
    return f"[{model}] → {prompt[:40]}..."


def postprocess(response: str) -> str:
    time.sleep(0.02)
    return response.strip().upper()


# ── Pipeline ──────────────────────────────────────────────────────────────────

with profiler.step("full_pipeline") as root:
    root.tag(version="1.0", dataset="customers_v3")

    # Step 1 — load
    with profiler.step("load_data") as s:
        records = load_dataset("customers")
        s.tag(records=len(records))

    # Step 2 — embed (one sub-step per record)
    with profiler.step("embed_records") as s:
        embeddings = []
        for record in records:
            with profiler.step(f"embed[{record['id']}]"):
                embeddings.append(embed_text(record["text"]))
        s.tag(total=len(embeddings))

    # Step 3 — inference
    with profiler.step("inference") as s:
        model = "gpt-4o-mini"
        s.tag(model=model, temperature=0.7)

        with profiler.step("build_prompt"):
            time.sleep(0.01)
            prompt = "Summarize: " + " | ".join(r["text"] for r in records[:3])

        with profiler.step("llm_call") as llm_s:
            response = call_llm(prompt, model)
            llm_s.tag(prompt_len=len(prompt), response_len=len(response))

    # Step 4 — postprocess
    with profiler.step("postprocess"):
        result = postprocess(response)


# ── Decorator example (with runs) ────────────────────────────────────────────

@profiler.measure("embed_benchmark", runs=5)
def embed_benchmark(text: str) -> list[float]:
    return embed_text(text)


embed_benchmark("benchmark input text")


# ── JSON export ───────────────────────────────────────────────────────────────

print("\n── JSON export ──────────────────────────────────────────────────")
print(profiler.to_json())
