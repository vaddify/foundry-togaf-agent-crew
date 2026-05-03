# Next Steps â€” AI Startup Team on Microsoft Foundry

All 24 project files are saved at `C:\Users\Kim\Documents\Options \ai-startup-team\`.
Follow these steps in order.

---

## 1. Prereqs (one-time, ~10 min)

```powershell
# Tools
winget install --id Microsoft.AzureCLI
winget install --id Astral-sh.uv          # fast Python package manager (or use pip)
winget install --id Docker.DockerDesktop  # only if you want local container builds; az acr build works without it

# Login
az login
az account set --subscription "<your-subscription-id>"
az extension add --name ml --upgrade
az extension add --name cognitiveservices --upgrade
```

---

## 2. Confirm Foundry quota in your region (~2 min)

```powershell
az cognitiveservices usage list --location eastus2 -o table
```

If GPT-5 / o4 / Claude Sonnet aren't available there, change `$Region` in
`scripts/provision.ps1` to `eastus`, `swedencentral`, or `westus3`.

---

## 3. Edit two files

- `scripts/provision.ps1` â†’ set `$Subscription` (and optionally region/names).
- `.env.example` â†’ save a copy as `.env` (you'll fill the endpoints after step 4).

---

## 4. Provision Azure (~15 min, mostly waiting on model deployments)

```powershell
cd 'C:\Users\Kim\Documents\Options \ai-startup-team'
./scripts/provision.ps1
```

Then in the **Foundry portal** â†’ your project â†’ **Connections** â†’ **+ New** â†’
**Grounding with Bing Search** (Bing connection can't be created via CLI yet).

---

## 5. Fill in real values

Copy the printed endpoints into:

- `.foundry/agent-metadata.yaml` â†’ `projectEndpoint`, `azureContainerRegistry`, `subscriptionId`
- `.env` â†’ `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_SEARCH_ENDPOINT`

---

## 6. Local smoke test (~5 min)

```powershell
uv venv ; .venv\Scripts\Activate.ps1
uv pip install -e .
python -m src.orchestrator.main "AI tutor for first-year college calculus students"
```

You should see all 5 agents produce output.

---

## 7. Deploy hosted agent

```powershell
./scripts/deploy.ps1
```

---

## 8. Run evals + auto-tune prompts

```powershell
./scripts/evaluate.ps1
```

Results land in `.foundry/results/`. Anything below 4.0 â†’ Prompt Optimizer
rewrites that agent's instructions and re-tests.

---

## 9. Publish to Teams

Follow `copilot-studio/wrapper-plan.md` (~30 min in the portal).

---

## When you're ready, ping Copilot with any of:

- *"Provision failed at step X"* â€” diagnose the Azure error.
- *"Install the Azure MCP server"* â€” drive deploy + eval + prompt optimization directly from chat.
- *"Add CrewAI / LangGraph version side-by-side"* â€” for A/B comparison.
- *"Wire up Azure AI Search memory ingestion"* â€” so agents remember past runs.

---

## File map (for quick reference)

| Path | Purpose |
|---|---|
| `README.md` | Project overview |
| `pyproject.toml` | Python deps |
| `.env.example` | Env var template |
| `.foundry/agent-metadata.yaml` | Foundry env config (dev/prod) |
| `.foundry/datasets/golden-set.jsonl` | 20-prompt eval set |
| `.foundry/evaluators/quality.yaml` | 6-criterion judge config |
| `src/orchestrator/main.py` | Workflow: Researcher â†’ Validator â†’ (Coder â€– PM â€– Outreach) |
| `src/orchestrator/server.py` | `/invocations` + `/health` HTTP surface |
| `src/orchestrator/agent.yaml` | Hosted-agent manifest |
| `src/orchestrator/Dockerfile` | Container image |
| `src/agents/*.py` | The 5 TOGAF-aligned specialist agents (Business Architect, Enterprise Architect, Solution Engineer, Implementation Manager, Stakeholder Engagement Lead) |
| `scripts/provision.ps1` | One-time Azure provisioning |
| `scripts/deploy.ps1` | Build + push + deploy |
| `scripts/evaluate.ps1` | Batch eval + Prompt Optimizer |
| `copilot-studio/wrapper-plan.md` | Teams distribution steps |

