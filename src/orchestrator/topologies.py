"""Workflow topologies for the AI startup-team orchestrator.

Selectable via the TOPOLOGY env var or the --topology CLI flag.

Topologies (all use the same 5 registered Foundry agents):

  simple   (default)   BA -> EA -> fan-out(SE, IM, SEL) -> join

  debate               BA -> EA -> BA' -> EA' -> fan-out(SE, IM, SEL) -> join
                       (BA' sees EA's critique and produces a revised brief;
                        EA' re-evaluates the revised brief.)

  routed               BA -> EA -> [router on GO/NO-GO/PIVOT]
                                 GO    -> fan-out(SE, IM, SEL) -> join
                                 PIVOT -> SE only                 -> join_solo
                                 NO-GO -> SEL only (kill memo)    -> join_solo

  full                 debate revision pass + routed switch + scratchpad context
                       (downstream agents receive BA brief + EA verdict prepended)

Pattern coverage:
  - Conversation between two agents -> debate / full
  - Lead/Router that picks who runs -> routed / full
  - Shared memory (scratchpad)      -> full
"""
from __future__ import annotations

import re
from typing import Any

from agent_framework import (
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    Case,
    Default,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)

from src.agents import (
    business_architect,
    enterprise_architect,
    solution_engineer,
    implementation_manager,
    stakeholder_engagement_lead,
)


# ---------------------------------------------------------------- helpers ---

def _agent_text(r: AgentExecutorResponse) -> str:
    return r.agent_response.text if r.agent_response is not None else ""


def _build_request(prompt: str) -> AgentExecutorRequest:
    """Wrap a string prompt in the message envelope agents expect."""
    return AgentExecutorRequest(
        messages=[Message(role="user", contents=[prompt])],
        should_respond=True,
    )


# Glue: convert AgentExecutorResponse -> str for routers/scratchpads.
@executor(id="resp_to_text")
async def resp_to_text(
    r: AgentExecutorResponse,
    ctx: WorkflowContext[str, str],
) -> None:
    await ctx.send_message(_agent_text(r))


# ---------------------------------------------------------------- joins ---

@executor(id="join")
async def join(
    responses: list[AgentExecutorResponse],
    ctx: WorkflowContext[None, str],
) -> None:
    """Aggregate parallel agents' outputs (1+ of them) into one final string."""
    sections = []
    for r in responses:
        sections.append(f"## {r.executor_id}\n\n{_agent_text(r)}")
    await ctx.yield_output("\n\n---\n\n".join(sections))


@executor(id="join_solo")
async def join_solo(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[None, str],
) -> None:
    """Single-agent terminator (NO-GO + PIVOT branches yield only one output)."""
    await ctx.yield_output(f"## {response.executor_id}\n\n{_agent_text(response)}")


# ============================================================ Pattern 1 ===
# Debate: BA produces a brief, EA critiques, BA revises in light of EA's
# critique, EA re-validates. Sequential, no conditional branching.

@executor(id="forge_revision_prompt")
async def forge_revision_prompt(
    ea_response: AgentExecutorResponse,
    ctx: WorkflowContext[AgentExecutorRequest, str],
) -> None:
    """Take EA's critique and ask BA to revise."""
    critique = _agent_text(ea_response)
    prompt = (
        "Below is the Enterprise Architect's critique of your initial market "
        "brief. Revise the brief to directly address each point: fill evidence "
        "gaps, drop unsupported claims, tighten the scope.\n\n"
        f"=== EA CRITIQUE ===\n{critique}"
    )
    await ctx.send_message(_build_request(prompt))


# ============================================================ Pattern 2 ===
# Router: switch downstream graph based on EA's GO / PIVOT / NO-GO verdict.

NOGO_RE  = re.compile(r"\bNO[\s-]?GO\b", re.IGNORECASE)
PIVOT_RE = re.compile(r"\bPIVOT\b",      re.IGNORECASE)


def _is_nogo(msg: str)  -> bool: return bool(NOGO_RE.search(msg))
def _is_pivot(msg: str) -> bool: return bool(PIVOT_RE.search(msg)) and not _is_nogo(msg)


@executor(id="kill_memo_router")
async def kill_memo_router(
    msg: str,
    ctx: WorkflowContext[AgentExecutorRequest, str],
) -> None:
    """NO-GO -> ask SEL to write a one-page kill memo."""
    prompt = (
        "The Enterprise Architect rejected this idea (NO-GO). Write a concise "
        "one-page 'kill memo' for the founding team explaining (1) why we are "
        "stopping, (2) which signals would change our mind, (3) what to do "
        "with work already done.\n\n"
        f"=== CONTEXT ===\n{msg}"
    )
    await ctx.send_message(_build_request(prompt))


@executor(id="pivot_router")
async def pivot_router(
    msg: str,
    ctx: WorkflowContext[AgentExecutorRequest, str],
) -> None:
    """PIVOT -> ask SE to propose 2-3 adjacent angles, no code yet."""
    prompt = (
        "The Enterprise Architect recommended PIVOT. Propose 2-3 adjacent "
        "angles on the original idea that better fit the constraints raised. "
        "For each, give a 1-paragraph thesis and a thinnest-possible MVP. "
        "Do NOT scaffold code yet.\n\n"
        f"=== CONTEXT ===\n{msg}"
    )
    await ctx.send_message(_build_request(prompt))


@executor(id="go_broadcast")
async def go_broadcast(
    msg: str,
    ctx: WorkflowContext[AgentExecutorRequest, str],
) -> None:
    """GO -> broadcast the same prompt to all 3 downstream agents."""
    await ctx.send_message(_build_request(msg))


# ============================================================ Pattern 3 ===
# Shared scratchpad: collect BA brief + EA verdict and forward both as a
# combined narrative to whichever downstream branch the router picks.

@executor(id="scratchpad")
async def scratchpad(
    msg: str,
    ctx: WorkflowContext[str, str],
) -> None:
    annotated = (
        "## Cumulative context for downstream agents\n\n"
        + msg
        + "\n\n## Your turn:\nProduce your section using the context above."
    )
    await ctx.send_message(annotated)


# =========================================================================
# Topology builders
# =========================================================================

def build_simple():
    """BA -> EA -> fan-out(SE, IM, SEL) -> join."""
    ba  = business_architect.build()
    ea  = enterprise_architect.build()
    se  = solution_engineer.build()
    im  = implementation_manager.build()
    sel = stakeholder_engagement_lead.build()
    return (
        WorkflowBuilder(start_executor=ba)
        .add_chain([ba, ea])
        .add_fan_out_edges(ea, [se, im, sel])
        .add_fan_in_edges([se, im, sel], join)
        .build()
    )


def build_debate():
    """BA -> EA -> [BA revises in light of EA] -> EA' -> fan-out -> join.

    Two passes. Acyclic (the second BA/EA are separate executor instances).
    """
    ba  = business_architect.build()
    ea  = enterprise_architect.build()
    ba_revise = AgentExecutor(business_architect.build(),   id="business_architect_revise")
    ea_revise = AgentExecutor(enterprise_architect.build(), id="enterprise_architect_revise")
    se  = solution_engineer.build()
    im  = implementation_manager.build()
    sel = stakeholder_engagement_lead.build()

    return (
        WorkflowBuilder(start_executor=ba)
        .add_chain([ba, ea, forge_revision_prompt, ba_revise, ea_revise])
        .add_fan_out_edges(ea_revise, [se, im, sel])
        .add_fan_in_edges([se, im, sel], join)
        .build()
    )


def build_routed():
    """BA -> EA -> switch(GO/PIVOT/NO-GO) -> different downstream sets."""
    ba  = business_architect.build()
    ea  = enterprise_architect.build()

    se_go   = AgentExecutor(solution_engineer.build(),         id="solution_engineer_go")
    im_go   = AgentExecutor(implementation_manager.build(),    id="implementation_manager_go")
    sel_go  = AgentExecutor(stakeholder_engagement_lead.build(), id="stakeholder_engagement_lead_go")
    se_solo = AgentExecutor(solution_engineer.build(),         id="solution_engineer_solo")
    sel_solo= AgentExecutor(stakeholder_engagement_lead.build(), id="stakeholder_engagement_lead_solo")

    return (
        WorkflowBuilder(start_executor=ba)
        .add_chain([ba, ea, resp_to_text])
        .add_switch_case_edge_group(
            resp_to_text,
            [
                Case(condition=_is_nogo,  target=kill_memo_router),
                Case(condition=_is_pivot, target=pivot_router),
                Default(target=go_broadcast),
            ],
        )
        # GO branch: fan out
        .add_fan_out_edges(go_broadcast, [se_go, im_go, sel_go])
        .add_fan_in_edges([se_go, im_go, sel_go], join)
        # PIVOT branch
        .add_edge(pivot_router, se_solo)
        .add_edge(se_solo, join_solo)
        # NO-GO branch
        .add_edge(kill_memo_router, sel_solo)
        .add_edge(sel_solo, join_solo)
        .build()
    )


def build_full():
    """Debate revision + routed switch + scratchpad context."""
    ba  = business_architect.build()
    ea  = enterprise_architect.build()
    ba_revise = AgentExecutor(business_architect.build(),   id="business_architect_revise")
    ea_revise = AgentExecutor(enterprise_architect.build(), id="enterprise_architect_revise")

    se_go    = AgentExecutor(solution_engineer.build(),         id="solution_engineer_go")
    im_go    = AgentExecutor(implementation_manager.build(),    id="implementation_manager_go")
    sel_go   = AgentExecutor(stakeholder_engagement_lead.build(),id="stakeholder_engagement_lead_go")
    se_solo  = AgentExecutor(solution_engineer.build(),         id="solution_engineer_solo")
    sel_solo = AgentExecutor(stakeholder_engagement_lead.build(),id="stakeholder_engagement_lead_solo")

    # BA -> EA -> revise prompt -> BA' -> EA' -> resp_to_text -> scratchpad -> switch
    return (
        WorkflowBuilder(start_executor=ba)
        .add_chain([
            ba, ea, forge_revision_prompt, ba_revise, ea_revise,
            resp_to_text, scratchpad,
        ])
        .add_switch_case_edge_group(
            scratchpad,
            [
                Case(condition=_is_nogo,  target=kill_memo_router),
                Case(condition=_is_pivot, target=pivot_router),
                Default(target=go_broadcast),
            ],
        )
        .add_fan_out_edges(go_broadcast, [se_go, im_go, sel_go])
        .add_fan_in_edges([se_go, im_go, sel_go], join)
        .add_edge(pivot_router, se_solo)
        .add_edge(se_solo, join_solo)
        .add_edge(kill_memo_router, sel_solo)
        .add_edge(sel_solo, join_solo)
        .build()
    )


TOPOLOGIES = {
    "simple": build_simple,
    "debate": build_debate,
    "routed": build_routed,
    "full":   build_full,
}


def build(name: str = "simple"):
    if name not in TOPOLOGIES:
        raise ValueError(f"Unknown topology '{name}'. Choose: {list(TOPOLOGIES)}")
    return TOPOLOGIES[name]()
