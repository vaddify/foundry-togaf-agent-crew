"""Hosted-agent HTTP surface (invocations protocol).

Exposes:
  POST /invocations  -> runs the orchestrator workflow
  GET  /health       -> liveness probe

Body fields:
  input:    str          (required)  the startup idea
  topology: str          (optional)  simple|debate|routed|full   (default: env TOPOLOGY or 'simple')
  threadId: str          (optional)  echoed back for client-side correlation
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .main import run

app = FastAPI(title="ai-startup-team")


class InvocationRequest(BaseModel):
    input: str
    topology: Optional[str] = None
    threadId: Optional[str] = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invocations")
async def invocations(req: InvocationRequest) -> dict:
    result = await run(req.input, topology=req.topology)
    return {
        "output": result["output"],
        "topology": result["topology"],
        "threadId": req.threadId,
    }
