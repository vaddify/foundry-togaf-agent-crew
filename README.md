# AI Startup Team - on Microsoft Foundry

A 5-agent "founding team" built with the **Microsoft Agent Framework** and deployed as a **hosted agent** on **Microsoft Foundry Agent Service**.

## Purpose

Demonstrate an end-to-end, production-grade reference implementation of a **multi-agent system on Microsoft Foundry** that takes a one-line startup idea and runs it through a TOGAF-aligned founding crew - market research, architecture review, MVP scaffolding, delivery plan, and go-to-market drafts - using best-fit models per role (GPT-5, Claude Sonnet 4.5, o4-mini, GPT-4.1) wired together with the Microsoft Agent Framework `WorkflowBuilder`.

## Objectives

1. **Show the right layering**: orchestration + agents + tools + memory + evals all live in Foundry; Copilot Studio is only the Teams/M365 distribution surface.
2. **Cover the three orchestration patterns** developers actually need:
   - sequential conversation between two agents (`debate` topology),
   - lead/router agent that picks downstream work (`routed` topology - GO / PIVOT / NO-GO),
   - shared memory across agents (`full` topology - debate + scratchpad + router).
3. **Real Azure, no fictional CLI**: provision Foundry project + model deployments, register Persistent Agents, build & push to ACR, deploy to Azure Container Apps, expose `/invocations`.
4. **Quantify quality**: batch eval against a 20-prompt golden set with `azure-ai-evaluation` (groundedness, relevance, coherence, fluency).
5. **Distribute to humans**: one-click import of [copilot-studio/openapi.yaml](copilot-studio/openapi.yaml) as a Power Platform Custom Connector to surface the crew in Teams.

| # | Agent (TOGAF role) | Model (suggested) | Job |
|---|---|---|---|
| 1 | Business Architect (Phase B) | `gpt-5` + Bing grounding | Market scan, competitor sweep, TAM/SAM/SOM |
| 2 | Enterprise Architect (Phase A) | `o4` (reasoning) | Pressure-test the idea, surface risks, GO/NO-GO/PIVOT |
| 3 | Solution Engineer (Phases C+D) | `claude-sonnet-4.5` | Build MVP scaffold via GitHub MCP |
| 4 | Implementation Manager (Phases F+G) | `gpt-4.1-mini` | 30-day plan, backlog, delivery governance |
| 5 | Stakeholder Engagement Lead (Stakeholder Mgmt + Phase H) | `gpt-4.1` + Graph | ICP, target accounts, cold emails (drafts only) |

Orchestrator routes the user's startup idea through the crew, agents share state via Foundry threads + Azure AI Search vector memory, results are evaluated against a golden dataset and prompts auto-tuned with the Foundry Prompt Optimizer.

## Stack

```
Orchestrator + 5 Agents â†’ Microsoft Foundry Agent Service
   â”œâ”€ Models: mix GPT-5, Claude Sonnet 4.5, o4, GPT-4.1-mini  (Foundry model catalog)
   â”œâ”€ Tools:  Bing grounding, GitHub MCP, Microsoft Graph (mail), File search
   â”œâ”€ Memory: Foundry thread state + Azure AI Search vector store
   â”œâ”€ Evals:  Foundry batch eval on a 20-prompt golden set
   â”œâ”€ Optim:  Foundry Prompt Optimizer per agent
   â””â”€ UI:     Publish to Teams via a Copilot Studio wrapper agent
```

## Quick start

```powershell
# 1. Provision Azure (one-time)
./scripts/provision.ps1

# 2. Deploy hosted agent
./scripts/deploy.ps1

# 3. Test
python -m src.orchestrator.main "I want to launch an AI tool for college esports teams"
```

## Folder layout

```
ai-startup-team/
â”œâ”€ .foundry/                    # Foundry workspace (metadata, evals, datasets)
â”œâ”€ src/
â”‚  â”œâ”€ orchestrator/             # Hosted agent entry point + Dockerfile
â”‚  â””â”€ agents/                   # 5 specialist agents
â”‚  â””â”€ tools/                    # Bing, GitHub, Graph mail
â”œâ”€ scripts/                     # provision.ps1, deploy.ps1
â”œâ”€ copilot-studio/              # Teams wrapper plan
â””â”€ README.md
```

See [copilot-studio/wrapper-plan.md](copilot-studio/wrapper-plan.md) for Teams distribution.

