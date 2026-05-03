# Contributing

Thanks for your interest in `ai-startup-team`.

## Dev setup

```powershell
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
ruff check src
```

## Adding / modifying an agent

1. Add the file under `src/agents/<role>.py` following the TOGAF naming convention.
2. Reuse `src.agents._base.make_agent` so credentials and Foundry wiring stay consistent.
3. Add the agent to `src/orchestrator/main.py` topology.
4. Add the agent name to the Prompt Optimizer loop in `scripts/evaluate.ps1`.
5. Add at least 2 prompts covering the new role to `.foundry/datasets/golden-set.jsonl`.

## PR checklist

- [ ] `ruff check src` passes
- [ ] CI green
- [ ] No secrets committed (`.env`, keys, endpoints with tokens)
- [ ] Updated `README.md` if behavior or topology changed