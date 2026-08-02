# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from unittest.mock import patch

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.property import StringProperty

# These tests only need an LLM config object and stub the chat model, so they run
# offline even under SKIP_LLM_TESTS=1.
pytestmark = pytest.mark.usefixtures("allow_llm_config_construction")


def _llm_config() -> OpenAiCompatibleConfig:
    return OpenAiCompatibleConfig(name="agent_llm", model_id="fake", url="null")


def test_managerworkers_infers_inputs_from_group_manager_prompt() -> None:
    """A ManagerWorkers exposes the group manager's prompt placeholders as inputs, so
    a flow AgentNode wrapping it declares input ports a DataFlowEdge can resolve."""
    cfg = _llm_config()
    manager = Agent(
        name="manager",
        llm_config=cfg,
        system_prompt="Translate the following to Arabic:\n\n{{joke}}\n\nMake {{count}} variants.",
    )
    worker = Agent(name="worker", llm_config=cfg, system_prompt="You translate.")
    mw = ManagerWorkers(name="mw", group_manager=manager, workers=[worker])

    assert sorted(p.title for p in (mw.inputs or [])) == ["count", "joke"]


def test_managerworkers_infers_outputs_from_group_manager() -> None:
    """Symmetric with inputs: a ManagerWorkers exposes the group manager's outputs."""
    cfg = _llm_config()
    manager = Agent(
        name="manager",
        llm_config=cfg,
        system_prompt="Answer the question.",
        outputs=[StringProperty(title="answer")],
    )
    worker = Agent(name="worker", llm_config=cfg, system_prompt="You help.")
    mw = ManagerWorkers(name="mw", group_manager=manager, workers=[worker])

    assert [p.title for p in (mw.outputs or [])] == ["answer"]


def test_managerworkers_runs_as_a_flow_step_with_data_edge_inputs() -> None:
    """A ManagerWorkers flow step loads with its data edge resolved and executes:
    loading proves the node exposes the ``joke`` input the edge targets, running
    proves the manager's answer comes back as the node's single string output."""
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
    from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode

    class _FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    # The final message has no tool_calls → the manager routes to END without delegating.
    fake_llm = _FakeModel(responses=[AIMessage(content="لماذا...")])

    cfg = _llm_config()
    joke = StringProperty(title="joke")
    translated = StringProperty(title="translated")

    manager = Agent(
        name="manager",
        llm_config=cfg,
        system_prompt="Translate the following to Arabic:\n\n{{joke}}",
        outputs=[translated],
    )
    worker = Agent(name="worker", llm_config=cfg, system_prompt="You translate.")
    mw = ManagerWorkers(name="translator", group_manager=manager, workers=[worker])
    assert [p.title for p in (mw.inputs or [])] == ["joke"]

    manager_node = AgentNode(name="manager_node", agent=mw)
    start_node = StartNode(name="start", inputs=[joke])
    end_node = EndNode(name="end", outputs=[translated])
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, manager_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=manager_node),
            ControlFlowEdge(name="node_to_end", from_node=manager_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="joke_edge",
                source_node=start_node,
                source_output=joke.title,
                destination_node=manager_node,
                destination_input=joke.title,
            ),
            DataFlowEdge(
                name="translated_edge",
                source_node=manager_node,
                source_output=translated.title,
                destination_node=end_node,
                destination_input=translated.title,
            ),
        ],
        outputs=[translated],
    )

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=lambda self_obj, llm_config, *a, **k: fake_llm,
    ), patch.object(
        FakeMessagesListChatModel,
        "bind_tools",
        new=lambda self_obj, *a, **k: self_obj,
    ):
        compiled = loader.load_component(flow)
        result = compiled.invoke(
            {
                "inputs": {"joke": "Why did the car..."},
                "messages": [{"role": "user", "content": ""}],
            },
            {"configurable": {"thread_id": "managerworkers-node"}},
        )

    assert result["outputs"]["translated"] == "لماذا..."
