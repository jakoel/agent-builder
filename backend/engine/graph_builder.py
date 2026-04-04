"""Build a LangGraph StateGraph from an AgentDefinition."""

from __future__ import annotations

import json
from typing import Any

from langgraph.graph import END, StateGraph

from .state import AgentState
from .tool_loader import load_tools
from ..schemas.agent import AgentDefinition
from ..services.ollama_service import OllamaService
from ..services.sandbox_service import SandboxService


def build_graph(
    agent_def: AgentDefinition,
    ollama_service: OllamaService,
    sandbox_service: SandboxService,
) -> Any:
    """Compile a LangGraph StateGraph from the agent's flow definition.

    Returns a compiled graph that can be invoked with an ``AgentState``.
    """
    flow = agent_def.flow
    if flow is None:
        raise ValueError("Agent has no flow definition")

    tool_callables = load_tools(agent_def.tools, sandbox_service)
    node_map = {n.id: n for n in flow.nodes}
    edge_map: dict[str, list] = {}
    for e in flow.edges:
        edge_map.setdefault(e.source, []).append(e)

    graph = StateGraph(AgentState)

    # ------------------------------------------------------------------
    # Create node functions
    # ------------------------------------------------------------------
    for node in flow.nodes:
        if node.type == "start":
            def _start(state: AgentState, _n=node) -> AgentState:
                state["current_node"] = _n.id
                return state
            graph.add_node(node.id, _start)

        elif node.type == "end":
            def _end(state: AgentState, _n=node) -> AgentState:
                state["current_node"] = _n.id
                return state
            graph.add_node(node.id, _end)

        elif node.type == "tool_call":
            async def _tool(state: AgentState, _n=node) -> AgentState:
                state["current_node"] = _n.id
                tool_fn = tool_callables.get(_n.tool_name or "")
                if tool_fn is None:
                    state["error"] = f"Tool '{_n.tool_name}' not found"
                    return state
                input_data = {
                    **(state.get("input_data") or {}),
                    **(state.get("tool_results") or {}),
                }
                result = await tool_fn(input_data)
                tr = state.get("tool_results") or {}
                tr[_n.tool_name or _n.id] = result
                state["tool_results"] = tr
                return state
            graph.add_node(node.id, _tool)

        elif node.type == "llm_call":
            async def _llm(state: AgentState, _n=node) -> AgentState:
                state["current_node"] = _n.id
                prompt = (_n.prompt_template or "{input}").format(
                    input=json.dumps(state.get("input_data", {})),
                    tool_results=json.dumps(state.get("tool_results", {})),
                )
                msgs = [{"role": "user", "content": prompt}]
                resp = await ollama_service.chat(
                    model=agent_def.model,
                    messages=msgs,
                    system=agent_def.system_prompt or None,
                )
                messages = state.get("messages") or []
                messages.append(resp)
                state["messages"] = messages
                tr = state.get("tool_results") or {}
                tr[f"llm_{_n.id}"] = resp
                state["tool_results"] = tr
                return state
            graph.add_node(node.id, _llm)

        elif node.type == "condition":
            def _cond(state: AgentState, _n=node) -> AgentState:
                state["current_node"] = _n.id
                return state
            graph.add_node(node.id, _cond)

    # ------------------------------------------------------------------
    # Wire edges
    # ------------------------------------------------------------------
    graph.set_entry_point(flow.entry_node)

    for node in flow.nodes:
        edges = edge_map.get(node.id, [])
        if not edges:
            continue

        if node.type == "end":
            graph.add_edge(node.id, END)
            continue

        if node.type == "condition" and len(edges) > 1:
            # Conditional routing
            condition_edges = edges

            def _router(state: AgentState, _edges=condition_edges) -> str:
                tool_results = state.get("tool_results", {})
                input_data = state.get("input_data", {})
                for edge in _edges:
                    if edge.condition:
                        try:
                            if eval(  # noqa: S307
                                edge.condition,
                                {"__builtins__": {}},
                                {"tool_results": tool_results, "input_data": input_data},
                            ):
                                return edge.target
                        except Exception:
                            continue
                # Fallback
                fallback = [e for e in _edges if not e.condition]
                return (fallback[0] if fallback else _edges[-1]).target

            targets = {e.target: e.target for e in edges}
            graph.add_conditional_edges(node.id, _router, targets)
        else:
            # Single deterministic edge
            target = edges[0].target
            target_node = node_map.get(target)
            if target_node and target_node.type == "end":
                graph.add_edge(node.id, END)
            else:
                graph.add_edge(node.id, target)

    return graph.compile()
