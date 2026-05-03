# AI Startup Team on Microsoft Foundry

A production-grade reference implementation of a **multi-agent system on Microsoft Foundry**.
A five-agent "founding team" — modeled after the TOGAF roles — takes a one-line startup
idea and runs it through market research, architecture review, MVP scaffolding, delivery
planning, and go-to-market drafts. Built with the **Microsoft Agent Framework**, deployed
as a hosted agent on **Azure Container Apps**, evaluated with **azure-ai-evaluation**, and
distributed to Microsoft Teams via a **Copilot Studio** wrapper.

---

## Purpose

Show how to build, deploy, evaluate, and distribute a real multi-agent system on
Microsoft's official agent stack — using best-fit models per role and the three
orchestration patterns developers actually need in production.

## Objectives

1. **Demonstrate the right layering.** Orchestration, agents, tools, memory, and
   evaluation all live in Foundry. Copilot Studio is only the Teams / M365
   distribution surface.
2. **Cover the three core orchestration patterns:**
   - Sequential conversation between two agents — the `debate` topology.
   - Lead/router agent that picks downstream work — the `routed` topology
     (GO / PIVOT / NO-GO).
   - Shared memory across agents — the `full` topology (debate + scratchpad + router).
3. **Use real Azure end-to-end, no fictional CLIs.** Provision a Foundry project and
   model deployments, register Persistent Agents, build and push to ACR, deploy to
   Azure Container Apps, expose `/invocations`.
4. **Quantify quality.** Batch-evaluate against a 20-prompt golden set with
   `azure-ai-evaluation` (groundedness, relevance, coherence, fluency).
5. **Distribute to humans.** Import [`copilot-studio/openapi.yaml`](copilot-studio/openapi.yaml)
   as a Power Platform Custom Connector to surface the crew in Microsoft Teams.

---

## The crew

| # | Agent (TOGAF role)                                     | Model               | Responsibility                                              |
|---|--------------------------------------------------------|---------------------|-------------------------------------------------------------|
| 1 | Business Architect (Phase B)                           | `gpt-5` + Bing      | Market scan, competitor sweep, TAM / SAM / SOM              |
| 2 | Enterprise Architect (Phase A)                         | `o4-mini`           | Pressure-test the idea, surface risks, GO / PIVOT / NO-GO   |
| 3 | Solution Engineer (Phases C + D)                       | `claude-sonnet-4.5` | MVP scaffold via GitHub MCP                                 |
| 4 | Implementation Manager (Phases F + G)                  | `gpt-4.1-mini`      | 30-day plan, backlog, delivery governance                   |
| 5 | Stakeholder Engagement Lead (Stakeholder Mgmt + Phase H) | `gpt-4.1` + Graph | ICP, target accounts, cold-email drafts                     |

---

## Stack

```
                Client (Teams / Copilot Studio / curl)
                                 |
                                 v
                  Azure Container Apps  ----  /health  /invocations
                                 |
                                 v
              Microsoft Agent Framework  WorkflowBuilder
                                 |
        +------------------------+------------------------+
        |                        |                        |
        v                        v                        v
   Foundry Persistent      Foundry model           Tools / Grounding
        Agents (5)         deployments              - Bing search
                            - gpt-5                 - GitHub MCP
                            - o4-mini               - Microsoft Graph (mail)
                            - gpt-4.1               - File search
                            - gpt-4.1-mini
                            - claude-sonnet-4.5
                                 |
                                 v
                       Memory + Evaluation
                          - Foundry thread state
                          - Azure AI Search vector store
                          - azure-ai-evaluation (groundedness / relevance /
                                                 coherence / fluency)
                          - Foundry Prompt Optimizer
```

### Topologies

The orchestrator selects a workflow topology via `--topology` CLI flag,
the `topology` field on `/invocations`, or the `TOPOLOGY` environment variable.

| Topology | Pattern                       | Flow                                                                 |
|----------|-------------------------------|----------------------------------------------------------------------|
| `simple` | Baseline                      | BA -> EA -> fan-out (SE, IM, SEL) -> join                            |
| `debate` | Two-agent conversation        | BA -> EA -> revise prompt -> BA' -> EA' -> fan-out -> join           |
| `routed` | Lead / router agent           | BA -> EA -> switch on GO / PIVOT / NO-GO -> branch-specific agents   |
| `full`   | All three patterns combined   | Debate revision + shared scratchpad + GO / PIVOT / NO-GO router      |

Implementation: [`src/orchestrator/topologies.py`](src/orchestrator/topologies.py).

---

## Quick start

Prerequisites: Azure CLI, Python 3.11+, PowerShell, and an Azure subscription with
Foundry quota.

```powershell
# 1. Provision Azure (one-time)
./scripts/provision.ps1

# 2. Register the five Persistent Agents in Foundry
./scripts/register-agents.ps1

# 3. Deploy the hosted orchestrator to Azure Container Apps
./scripts/deploy.ps1

# 4. Run locally
python -m src.orchestrator.main --topology routed `
    "I want to launch an AI tool for college esports teams"

# 5. Run the batch eval
./scripts/evaluate.ps1 -EndpointUrl https://<your-app>.azurecontainerapps.io
```

---

## Repository layout

```
ai-startup-team/
  .foundry/
    agent-metadata.yaml            Foundry project metadata
    datasets/golden-set.jsonl      20-prompt evaluation set
    evaluators/quality.yaml        Evaluator configuration
  src/
    agents/                        Five specialist agents
      _base.py                     Common FoundryAgent factory
      business_architect.py
      enterprise_architect.py
      solution_engineer.py
      implementation_manager.py
      stakeholder_engagement_lead.py
    orchestrator/
      topologies.py                The three orchestration patterns
      main.py                      CLI entry point
      server.py                    FastAPI /invocations surface
      evaluate.py                  Batch evaluator
      register_agents.py           Foundry Persistent Agent registration
      Dockerfile
      agent.yaml
  scripts/
    provision.ps1                  Provision Foundry project + Container Apps env
    deploy.ps1                     ACR build + Container App revision
    evaluate.ps1                   Batch eval wrapper
    register-agents.ps1            Wrapper for register_agents.py
    publish-to-github.ps1          Safety-scanned GitHub publisher
  copilot-studio/
    openapi.yaml                   Power Platform Custom Connector spec
    wrapper-plan.md                Teams distribution steps
```

---

## API

The hosted orchestrator exposes two endpoints:

- `GET  /health` — liveness probe.
- `POST /invocations` — runs the workflow.

Request body:

```json
{
  "input":    "AI tutor for first-year college calculus students",
  "topology": "routed",
  "threadId": "optional-client-correlation-id"
}
```

Response body:

```json
{
  "output":   "<aggregated markdown report from the crew>",
  "topology": "routed",
  "threadId": "optional-client-correlation-id"
}
```

---

## Evaluation

Run a batch eval against the deployed endpoint:

```powershell
python -m src.orchestrator.evaluate `
    --mode endpoint `
    --endpoint-url https://<your-app>.azurecontainerapps.io `
    --judge-model gpt-4.1
```

Scores are written to `.foundry/results/eval-<timestamp>.json` and printed to
the console as mean values per evaluator.

---

## Distribution to Microsoft Teams

The fastest path is the OpenAPI Custom Connector:

1. Power Platform admin -> Data -> Custom connectors -> New -> Import OpenAPI file.
2. Upload [`copilot-studio/openapi.yaml`](copilot-studio/openapi.yaml).
3. In Copilot Studio, create a topic that calls the `RunStartupCrew` action.
4. Channels -> Microsoft Teams -> Turn on -> Publish.

Full instructions: [`copilot-studio/wrapper-plan.md`](copilot-studio/wrapper-plan.md).

---

## License

See [LICENSE](LICENSE).
