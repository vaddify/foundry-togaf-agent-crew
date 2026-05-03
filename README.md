# AI Startup Team on Microsoft Foundry

<p align="center">
  <img src="docs/hero.png" alt="Foundry TOGAF Agent Crew - five specialist agents collaborating on Microsoft Foundry" width="820"/>
</p>

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

## Industry use cases

The crew is industry-agnostic — every role maps to a function that exists in any
sector. Swap the input prompt and tool-grounding sources; the orchestration is
unchanged.

### Pharmaceuticals & Life Sciences
- **Input:** "Late-phase asset for treatment-resistant depression — what's the
  go-to-market?"
- **Business Architect** scans clinical-trial registries, payer landscape, KOL
  publications.
- **Enterprise Architect** flags FDA labelling risk, REMS requirements, ICER
  pushback scenarios → GO / PIVOT / NO-GO.
- **Solution Engineer** scaffolds an HCP portal MVP (sample request, MSL chat).
- **Implementation Manager** plans launch readiness across medical, market access,
  commercial.
- **Stakeholder Engagement Lead** drafts payer dossiers, KOL outreach, patient-
  advocacy briefings.

### Retail & Consumer Goods
- **Input:** "Launch a private-label clean-beauty line in 6 months."
- **BA** runs category share, SKU gap analysis, social-listening on incumbents.
- **EA** stress-tests margin, returns rate, regulatory (INCI, FDA cosmetics).
- **SE** builds a Shopify storefront + subscription-engine scaffold.
- **IM** sequences supplier sourcing → packaging → DC slotting → launch windows.
- **SEL** drafts influencer briefs, retailer line-review decks, PR pitches.

### Automotive & Mobility
- **Input:** "Subscription-based EV battery health monitoring for fleets."
- **BA** sizes commercial-fleet TAM, OEM partnership landscape, telematics
  competitors.
- **EA** reviews ISO 26262 / UNECE R155 cybersecurity, OTA architecture risk.
- **SE** scaffolds ingest pipeline (CAN bus → Azure IoT → Fabric).
- **IM** plans pilot with one fleet operator → multi-region rollout.
- **SEL** drafts fleet-manager outreach, OEM BD memos, dealer-network FAQs.

### Banking & Financial Services
- **Input:** "AI-assisted SMB credit underwriting for community banks."
- **BA** profiles target banks (asset size, core platform), competitive
  intelligence on Numerated, Biz2X, Upstart.
- **EA** addresses fair-lending (ECOA), model risk (SR 11-7), explainability,
  vendor-risk assessment.
- **SE** scaffolds the underwriting API, decision-record store, audit log.
- **IM** plans SOC 2 readiness → pilot bank → core integration.
- **SEL** drafts CRO/CCO outreach, compliance-officer one-pagers, pilot MSAs.

### Manufacturing & Industrial
- **Input:** "Predictive maintenance SaaS for mid-market discrete manufacturers."
- **BA** maps NAICS subsectors, PLM/MES install base, downtime-cost benchmarks.
- **EA** evaluates OT/IT segregation, Purdue Model alignment, IEC 62443.
- **SE** scaffolds edge-collector + Azure IoT Operations + anomaly model.
- **IM** plans plant-pilot → multi-site rollout → MRO integration.
- **SEL** drafts plant-manager outreach, ROI calculators, channel-partner kits.

### Healthcare Providers & Payers
- **Input:** "Ambient documentation for community-health primary-care clinics."
- **BA** sizes target clinics, EHR install base, competitive landscape (Abridge,
  Nuance, Suki).
- **EA** addresses HIPAA, BAA flow, PHI residency, EHR integration risk.
- **SE** scaffolds capture app + EHR write-back via FHIR.
- **IM** plans clinical-pilot governance, training, change management.
- **SEL** drafts CMO outreach, ROI per encounter, payer-partnership memos.

### Energy & Utilities
- **Input:** "Virtual power plant aggregator for residential battery owners."
- **BA** maps ISO/RTO market structures, DR program revenue stacks.
- **EA** evaluates ISO interconnection, IEEE 2030.5 / OpenADR, cyber.
- **SE** scaffolds device-control gateway + bid-stack engine.
- **IM** plans utility-pilot, regulatory filings, customer onboarding.
- **SEL** drafts utility BD outreach, regulator briefings, homeowner FAQs.

### Public Sector & GovTech
- **Input:** "AI casework triage for state unemployment-insurance agencies."
- **BA** profiles agency procurement vehicles (StateRAMP, NASCIO themes), peer
  deployments.
- **EA** reviews FedRAMP/StateRAMP Moderate, accessibility (Section 508),
  bias-audit obligations.
- **SE** scaffolds case-router + adjudicator workbench.
- **IM** plans agency pilot, compliance documentation, change management.
- **SEL** drafts CIO/Commissioner outreach, legislative briefings, vendor-list
  applications.

### Pattern: how to adapt the crew to a new vertical

1. Edit each agent's `INSTRUCTIONS` constant in [`src/agents/`](src/agents/) to
   add domain context (regulatory regime, buyer personas, vocabulary).
2. Swap or add tool grounding — for regulated industries, give the Business
   Architect access to the regulator's public corpus via Azure AI Search.
3. Add a few vertical-specific rows to the golden eval set in
   [`.foundry/datasets/golden-set.jsonl`](.foundry/datasets/golden-set.jsonl) so
   regressions surface immediately.
4. Pick a topology: `routed` for portfolios where many ideas are NO-GO; `debate`
   when domain risk is high and you want explicit critique-revision; `full` when
   both apply.

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
