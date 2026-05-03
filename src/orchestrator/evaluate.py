"""Real batch evaluator for the ai-startup-team orchestrator.

Uses Azure AI Evaluation SDK (azure-ai-evaluation) — NO fictional CLI.

Two modes:
  --mode local     : run orchestrator in-process (default; no deployment needed)
  --mode endpoint  : POST to a deployed Container App's /invocations

Evaluators (all real, from azure.ai.evaluation):
  - GroundednessEvaluator    : is the answer supported by the input?
  - RelevanceEvaluator       : does the answer address the input?
  - CoherenceEvaluator       : is the answer well-structured?
  - FluencyEvaluator         : is the answer well-written?

The judge model uses MODEL_VALIDATOR (e.g. o4-mini) by default — overridable
via --judge-model.

Outputs:
  .foundry/results/eval-<timestamp>.json   (per-row scores)
  Console table with mean scores per evaluator.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


def load_dataset(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL dataset where each row has at least an 'input' or 'query' key."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_query(row: dict[str, Any]) -> str:
    for k in ("query", "input", "question", "prompt"):
        if k in row and isinstance(row[k], str):
            return row[k]
    raise ValueError(f"Dataset row missing query/input/question/prompt: {row}")


async def target_local(query: str) -> dict[str, str]:
    """Run the orchestrator workflow in-process."""
    from src.orchestrator.main import run as run_workflow
    result = await run_workflow(query)
    return {"response": result["output"]}


async def target_endpoint(query: str, endpoint_url: str) -> dict[str, str]:
    """POST to a deployed /invocations endpoint, with retries on 429/5xx."""
    url = endpoint_url.rstrip("/") + "/invocations"
    delays = [10, 30, 60, 120]  # seconds
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=600.0) as client:
        for attempt, delay in enumerate([0, *delays]):
            if delay:
                print(f"    retry in {delay}s (attempt {attempt})...", flush=True)
                await asyncio.sleep(delay)
            try:
                r = await client.post(url, json={"input": query})
                if r.status_code in (429, 500, 502, 503, 504):
                    last_exc = httpx.HTTPStatusError(
                        f"transient {r.status_code}", request=r.request, response=r
                    )
                    continue
                r.raise_for_status()
                return {"response": r.json().get("output", "")}
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exc = e
                continue
    raise last_exc if last_exc else RuntimeError("endpoint failed")


async def gather_responses(
    queries: list[str], mode: str, endpoint_url: str | None
) -> list[dict[str, str]]:
    """Run the target on every query (sequential to avoid model TPM throttling)."""
    out: list[dict[str, str]] = []
    for i, q in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {q[:70]}...", flush=True)
        if mode == "endpoint":
            assert endpoint_url, "--endpoint-url required for endpoint mode"
            r = await target_endpoint(q, endpoint_url)
        else:
            r = await target_local(q)
        out.append({"query": q, "response": r["response"]})
    return out


def run_evaluators(rows: list[dict[str, str]], judge_model: str) -> dict[str, Any]:
    """Score each (query, response) pair with the AI Evaluation SDK."""
    from azure.ai.evaluation import (
        evaluate,
        GroundednessEvaluator,
        RelevanceEvaluator,
        CoherenceEvaluator,
        FluencyEvaluator,
    )

    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    # The SDK accepts an Azure OpenAI / Foundry model_config dict.
    # For Foundry projects, it discovers models via the project endpoint.
    model_config = {
        "azure_endpoint": project_endpoint.split("/api/projects/")[0],
        "azure_deployment": judge_model,
        # 2024-12-01-preview or later required for o-series; safe for gpt-4.1 too.
        "api_version": "2025-01-01-preview",
    }

    # Write rows to a temp JSONL the SDK can read.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        data_path = f.name

    print("  scoring with judge:", judge_model)
    results = evaluate(
        data=data_path,
        evaluators={
            "groundedness": GroundednessEvaluator(model_config),
            "relevance": RelevanceEvaluator(model_config),
            "coherence": CoherenceEvaluator(model_config),
            "fluency": FluencyEvaluator(model_config),
        },
        evaluator_config={
            "groundedness": {"column_mapping": {"query": "${data.query}", "response": "${data.response}", "context": "${data.query}"}},
            "relevance":   {"column_mapping": {"query": "${data.query}", "response": "${data.response}"}},
            "coherence":   {"column_mapping": {"query": "${data.query}", "response": "${data.response}"}},
            "fluency":     {"column_mapping": {"response": "${data.response}"}},
        },
    )
    Path(data_path).unlink(missing_ok=True)
    return results


def print_summary(results: dict[str, Any]) -> None:
    metrics = results.get("metrics", {})
    print("\n=== Mean scores ===")
    for k, v in sorted(metrics.items()):
        print(f"  {k:<40} {v:.3f}" if isinstance(v, (int, float)) else f"  {k:<40} {v}")
    studio_url = results.get("studio_url")
    if studio_url:
        print(f"\nFoundry studio: {studio_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run batch eval against the orchestrator.")
    parser.add_argument("--mode", choices=["local", "endpoint"], default="local")
    parser.add_argument("--endpoint-url", help="Container App URL (for --mode endpoint)")
    parser.add_argument("--dataset", default=".foundry/datasets/golden-set.jsonl")
    parser.add_argument("--limit", type=int, default=None,
                        help="Run only the first N rows (smoke test).")
    parser.add_argument("--judge-model", default=os.environ.get("MODEL_VALIDATOR", "o4-mini"))
    parser.add_argument("--out", default=None, help="Output JSON path.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 1
    rows = load_dataset(dataset_path)
    if args.limit:
        rows = rows[: args.limit]
    queries = [normalize_query(r) for r in rows]

    print(f"==> Running orchestrator on {len(queries)} prompts (mode={args.mode})")
    responses = asyncio.run(gather_responses(queries, args.mode, args.endpoint_url))

    print(f"\n==> Scoring {len(responses)} responses")
    results = run_evaluators(responses, judge_model=args.judge_model)

    out_path = Path(args.out) if args.out else Path(
        f".foundry/results/eval-{datetime.now():%Y%m%d-%H%M}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        # results may contain non-JSON-serializable items; coerce.
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {out_path}")

    print_summary(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
