# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ast
from typing import Any

import pytest

from pyagentspec import Agent
from pyagentspec.adapters.openaiagents import AgentSpecLoader
from pyagentspec.adapters.openaiagents.flows._flow_ir import IRNode
from pyagentspec.adapters.openaiagents.flows.rulepacks.v0_3_3 import codegen
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import OpenAiConfig


def _contains_import_call(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "__import__":
                return True
    return False


def test_generated_flow_keeps_system_prompt_inside_string_literal() -> None:
    malicious_prompt = (
        "You are helpful.\n"
        '""",\n'
        ")\n"
        '__import__("os").system("touch /tmp/agentspec_codegen_pwned")\n'
        "dummy = Agent(\n"
        '  name="dummy",\n'
        '  instructions="""'
    )
    agent = Agent(
        name="A",
        llm_config=OpenAiConfig(name="m", model_id="gpt-4o-mini"),
        system_prompt=malicious_prompt,
    )
    start = StartNode(name="start")
    agent_node = AgentNode(name="agent_node", agent=agent)
    end = EndNode(name="end")
    flow = Flow(
        name="F",
        start_node=start,
        nodes=[start, agent_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_agent", from_node=start, to_node=agent_node),
            ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end),
        ],
    )

    generated = AgentSpecLoader().load_component(flow)
    tree = ast.parse(generated)

    assert not _contains_import_call(tree)


def test_generated_tool_error_message_quotes_tool_name_safely() -> None:
    malicious_name = "missing'); __import__('os').system('touch /tmp/tool_pwned'); #"
    lines, _needs_function_tool = codegen._emit_tools(
        [{"name": malicious_name, "inputs": [], "outputs": []}]
    )

    tree = ast.parse("\n".join(lines))

    assert not _contains_import_call(tree)


@pytest.mark.parametrize("setting_name", ["temperature", "top_p", "max_tokens"])
def test_generated_model_settings_reject_non_numeric_values(
    monkeypatch: pytest.MonkeyPatch, setting_name: str
) -> None:
    def _fake_parse_agent_yaml(_agent_yaml: str) -> dict[str, Any]:
        return {
            "name": "agent",
            "system_prompt": "hello",
            "llm_config": {
                "model_id": "gpt-4o-mini",
                "default_generation_parameters": {
                    setting_name: "__import__('os').system('touch /tmp/settings_pwned')"
                },
            },
        }

    monkeypatch.setattr(codegen, "_parse_agent_yaml", _fake_parse_agent_yaml)
    node = IRNode(id="agent", name="agent", kind="agent", meta={"agent_spec_yaml": "unused"})

    with pytest.raises(TypeError, match=setting_name):
        codegen._emit_agents([node])
