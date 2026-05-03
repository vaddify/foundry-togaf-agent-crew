"""Register the 5 TOGAF agents as Foundry Persistent Agents.

Idempotent: re-running creates a new version of each agent (versions are
immutable; the latest version is what `FoundryAgent` resolves by default).

Result: each agent shows up in Foundry portal -> Project -> Agents tab
with its own threads/runs/traces.

Tools attached:
  - business_architect       : Bing Grounding (real-time web evidence)
  - solution_engineer        : MCP (GitHub) when GITHUB_MCP_URL is set
  - others                   : no tools (pure prompt agents)
"""
from __future__ import annotations

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
    MCPTool,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Reuse the same instructions the local agents use.
from src.agents.business_architect       import INSTRUCTIONS as BA_INST
from src.agents.enterprise_architect     import INSTRUCTIONS as EA_INST
from src.agents.solution_engineer        import INSTRUCTIONS as SE_INST
from src.agents.implementation_manager   import INSTRUCTIONS as IM_INST
from src.agents.stakeholder_engagement_lead import INSTRUCTIONS as SEL_INST

load_dotenv()


# Connection id for the Bing Grounding resource (from `connections.get(...)`)
BING_CONN_ID = (
    "/subscriptions/52b8df4d-506e-4b20-9ee7-d90289c7280b"
    "/resourceGroups/rg-ai-startup-team"
    "/providers/Microsoft.CognitiveServices/accounts/fnd-ai-startup-team"
    "/projects/ai-startup-team/connections/bingaistartupteam"
)


def bing_tool() -> BingGroundingTool:
    return BingGroundingTool(
        bing_grounding=BingGroundingSearchToolParameters(
            search_configurations=[
                BingGroundingSearchConfiguration(
                    project_connection_id=BING_CONN_ID,
                    count=5,
                    market="en-US",
                    set_lang="en",
                )
            ]
        )
    )


def github_mcp_tool() -> MCPTool | None:
    url = os.environ.get("GITHUB_MCP_URL")
    if not url:
        return None
    return MCPTool(
        server_label="github",
        server_url=url,
    )


AGENTS = [
    {
        "name": "business-architect",
        "description": "TOGAF Phase B - market scan, competitors, TAM/SAM/SOM",
        "model_env": "MODEL_RESEARCHER",
        "instructions": BA_INST,
        "tools_factory": lambda: [bing_tool()],
    },
    {
        "name": "enterprise-architect",
        "description": "TOGAF Phase A - vision, risks, scoring, GO/NO-GO",
        "model_env": "MODEL_VALIDATOR",
        "instructions": EA_INST,
        "tools_factory": lambda: [],
    },
    {
        "name": "solution-engineer",
        "description": "TOGAF Phases C+D - MVP scaffold and runnable code",
        "model_env": "MODEL_CODER",
        "instructions": SE_INST,
        "tools_factory": lambda: [t for t in [github_mcp_tool()] if t is not None],
    },
    {
        "name": "implementation-manager",
        "description": "TOGAF Phases F+G - 30-day plan and backlog",
        "model_env": "MODEL_PM",
        "instructions": IM_INST,
        "tools_factory": lambda: [],
    },
    {
        "name": "stakeholder-engagement-lead",
        "description": "Stakeholder Mgmt + Phase H - outreach plan",
        "model_env": "MODEL_OUTREACH",
        "instructions": SEL_INST,
        "tools_factory": lambda: [],
    },
]


def main() -> int:
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

    print(f"==> Registering {len(AGENTS)} agents in {endpoint}")

    for spec in AGENTS:
        name = spec["name"]
        model = os.environ[spec["model_env"]]
        tools = spec["tools_factory"]()
        print(f"  - {name:<32} model={model:<12} tools={[t['type'] for t in tools] if tools else '[]'}")

        definition = PromptAgentDefinition(
            kind="prompt",
            model=model,
            instructions=spec["instructions"],
            tools=tools or None,
            # NOTE: omitting temperature on purpose. gpt-5 / o4-mini reject it,
            # and the default is fine for the other models.
        )
        version = client.agents.create_version(
            agent_name=name,
            definition=definition,
            description=spec["description"],
        )
        v = getattr(version, "version", None) or getattr(version, "name", "?")
        print(f"      registered version={v}")

    print("\n==> Done. View agents at:")
    print(f"   https://ai.azure.com  ->  ai-startup-team  ->  Agents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
