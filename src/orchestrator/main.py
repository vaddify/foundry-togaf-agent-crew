"""Hosted-agent entry point: orchestrator that routes the user's idea
through the 5-agent crew using Microsoft Agent Framework workflows.

Topology is selectable via:
  - TOPOLOGY environment variable (simple|debate|routed|full)
  - --topology CLI flag (overrides env)

See src/orchestrator/topologies.py for the diagrams + builders.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from dotenv import load_dotenv

from src.orchestrator.topologies import build as build_workflow

load_dotenv()


async def run(idea: str, topology: str | None = None) -> dict[str, Any]:
    name = topology or os.environ.get("TOPOLOGY", "simple")
    workflow = build_workflow(name)
    result = await workflow.run(idea)
    outputs = result.get_outputs()
    final_output = "\n\n".join(str(o) for o in outputs) if outputs else "<no output>"
    return {"idea": idea, "topology": name, "output": final_output}


def main() -> None:
    p = argparse.ArgumentParser(description="Run the AI startup-team orchestrator.")
    p.add_argument("idea", nargs="+", help="The startup idea to evaluate.")
    p.add_argument("--topology", choices=["simple", "debate", "routed", "full"],
                   default=None,
                   help="Workflow topology (defaults to TOPOLOGY env var or 'simple').")
    args = p.parse_args()

    idea = " ".join(args.idea)
    out = asyncio.run(run(idea, topology=args.topology))

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write(f"# topology: {out['topology']}\n\n")
    sys.stdout.write(out["output"])
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
