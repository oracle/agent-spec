# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import VllmConfig
from pyagentspec.property import StringProperty

from ....retry_test import retry_test


@pytest.fixture()
def agent_flow() -> Flow:
    nationality_property = StringProperty(title="nationality")
    car_property = StringProperty(title="car")
    llm_config = VllmConfig(
        name="llm_config",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.environ.get("LLAMA70BV33_API_URL"),
    )
    agent = Agent(
        name="agent",
        llm_config=llm_config,
        system_prompt="What is the fastest {{nationality}} car?",
        inputs=[nationality_property],
        outputs=[car_property],
    )
    agent_node = AgentNode(
        name="agent_node",
        agent=agent,
    )
    start_node = StartNode(name="start", inputs=[nationality_property])
    end_node = EndNode(name="end", outputs=[car_property])

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, agent_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=agent_node),
            ControlFlowEdge(name="node_to_end", from_node=agent_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=nationality_property.title,
                destination_node=agent_node,
                destination_input=nationality_property.title,
            ),
            DataFlowEdge(
                name="car_edge",
                source_node=agent_node,
                source_output=car_property.title,
                destination_node=end_node,
                destination_input=car_property.title,
            ),
        ],
        outputs=[car_property],
    )

    return flow


@retry_test(max_attempts=3, wait_between_tries=2)
def test_agentnode_can_be_imported_and_executed(agent_flow: Flow) -> None:
    """
    Failure rate:          0 out of 50
    Observed on:           2026-05-11
    Average success time:  0.46 seconds per successful attempt
    Average failure time:  No time measurement
    Max attempt:           3
    Justification:         (0.02 ** 3) ~= 0.7 / 100'000
    """

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(agent_flow)
    result = agent.invoke(
        {"inputs": {"nationality": "italian"}, "messages": [{"role": "user", "content": ""}]}
    )

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "car" in outputs


def test_single_string_output_taken_from_final_message_without_structured_generation() -> None:
    """The stub model has no structured output, so if the converter still attached a
    ``response_format`` the output would come back empty instead of holding "42".
    """
    from unittest.mock import patch

    from langchain_core.language_models.fake_chat_models import (
        FakeMessagesListChatModel,
    )
    from langchain_core.messages import AIMessage
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig

    class _FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    fake_llm = _FakeModel(responses=[AIMessage(content="42")])

    answer = StringProperty(title="answer")
    agent = Agent(
        name="agent",
        llm_config=OpenAiCompatibleConfig(name="agent_llm", model_id="fake", url="null"),
        system_prompt="Answer the question.",
        outputs=[answer],
    )
    agent_node = AgentNode(name="agent_node", agent=agent)
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[answer])
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, agent_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=agent_node),
            ControlFlowEdge(name="node_to_end", from_node=agent_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="answer_edge",
                source_node=agent_node,
                source_output=answer.title,
                destination_node=end_node,
                destination_input=answer.title,
            ),
        ],
        outputs=[answer],
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
            {"inputs": {}, "messages": [{"role": "user", "content": "What is 6*7?"}]},
            {"configurable": {"thread_id": "agentnode-single-string"}},
        )

    assert result["outputs"]["answer"] == "42"


@pytest.mark.anyio
@retry_test(max_attempts=3, wait_between_tries=2)
async def test_agentnode_can_be_executed_async(agent_flow: Flow) -> None:
    """
    Failure rate:          0 out of 50
    Observed on:           2026-05-11
    Average success time:  0.48 seconds per successful attempt
    Average failure time:  No time measurement
    Max attempt:           3
    Justification:         (0.02 ** 3) ~= 0.7 / 100'000
    """

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(agent_flow)
    result = await agent.ainvoke({"inputs": {"nationality": "italian"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "car" in outputs
