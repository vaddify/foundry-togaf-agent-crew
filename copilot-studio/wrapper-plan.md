# Teams Distribution: Copilot Studio Wrapper

The hosted Foundry agent is callable from anything that can hit `/invocations`.
The fastest way to put it in front of users is a thin **Copilot Studio agent**
that forwards messages to the Foundry agent.

## Steps (≈30 minutes in the portal)

### Fast path — import the OpenAPI spec as a Custom Connector

1. **Power Platform admin → Data → Custom connectors → New → Import OpenAPI file**.
   Upload [`copilot-studio/openapi.yaml`](openapi.yaml). This creates a connector with two actions: `RunStartupCrew` and `Health`.
2. **Copilot Studio → Create agent → "Skill"** (blank).
   - Name: `AI Startup Team`
   - Description: "Founding crew of 5 AI agents — research, validate, build, plan, outreach."
3. **Add a topic** named `Run startup crew`.
   - Trigger phrases: `build my startup`, `validate my idea`, `start a project`.
   - Slot: capture the user's idea as `Topic.idea` (string, required).
4. **Add an action → "Call a custom connector" → AI Startup Team → RunStartupCrew**.
   - `input` = `Topic.idea`
   - `topology` = `simple` (or `debate` / `routed` / `full`)
   - `threadId` = `System.Conversation.Id`
   - Save the response `output` into `Topic.result`.
5. **Send a message** with `Topic.result` (Markdown formatting toggle ON).
6. **Channels → Microsoft Teams → Turn on**. Publish.

### Manual path (if you can't create custom connectors)
   - URL: `https://<foundry-project-endpoint>/agents/ai-startup-team/invocations`
   - Method: POST
   - Auth: **Microsoft Entra (Service-to-service)** — assign Copilot Studio's managed identity the `Cognitive Services User` role on the Foundry project.
   - Body:
     ```json
     {
       "input": "{Topic.idea}",
       "threadId": "{System.Conversation.Id}"
     }
     ```
   - Save the response `output` into `Topic.result`.

4. **Send a message** with `Topic.result` (use Markdown formatting toggle ON).

5. **Channels → Microsoft Teams → Turn on**. Publish.
   The agent now appears in the Teams app store for your tenant.

## Why this wrapper instead of building it natively in Copilot Studio
- All multi-agent orchestration, model selection (Claude!), tools, evals, and prompt optimization stay in Foundry — the right layer.
- Copilot Studio just handles **identity, channels, and UX** (Teams, Outlook, M365 Copilot).
- Swap models or rewire agents in Foundry; Teams users see no change.

## Optional upgrades
- Add a **second topic** "Send drafted email" that calls a separate Foundry endpoint with human-in-the-loop approval before invoking Microsoft Graph.
- Add **Power Automate** flow on the response to log every run to a SharePoint list for analytics.
