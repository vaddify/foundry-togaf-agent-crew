"""Shared agent factory using Microsoft Agent Framework + Foundry.

API verified against agent-framework 1.2.2 + agent-framework-foundry 1.2.2.

We use `FoundryAgent`, which connects to a server-registered Foundry
Persistent Agent (created via `scripts/register-agents.ps1`). This means
each agent shows up in the Foundry portal with its own threads, runs,
traces, and tool wiring (Bing Grounding, MCP, etc.).
"""
from __future__ import annotations

import os
from agent_framework_foundry import FoundryAgent
from azure.identity import DefaultAzureCredential


def make_agent(
    *,
    name: str,
    model_env: str = "",        # kept for backward compatibility; ignored
    instructions: str = "",     # kept for backward compatibility; ignored
    tools: list | None = None,  # kept for backward compatibility; ignored
    foundry_agent_name: str | None = None,
) -> FoundryAgent:
    """Build a Foundry-registered agent reference.

    The agent's model, instructions, and tools live server-side in Foundry
    (set by ``scripts/register-agents.ps1``). This factory just resolves
    a client connection to the named agent.
    """
    agent_name = foundry_agent_name or name
    return FoundryAgent(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        agent_name=agent_name,
        credential=DefaultAzureCredential(),
        allow_preview=True,   # PromptAgent run uses preview session APIs
    )
