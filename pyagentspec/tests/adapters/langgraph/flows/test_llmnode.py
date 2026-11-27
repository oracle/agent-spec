# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.llms import LlmConfig, LlmGenerationConfig, VllmConfig
from pyagentspec.property import Property, StringProperty

from ....retry_test import retry_test


def test_llmnode_structured_output_schema_has_description(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structured output schemas include the metadata required by tool-based providers."""
    from pyagentspec.adapters.langgraph import _node_execution

    class FakeChatModel:
        def __init__(self) -> None:
            self.captured_schema: dict | None = None

        def with_structured_output(self, schema: dict) -> object:
            self.captured_schema = schema
            return object()

    monkeypatch.setattr(_node_execution, "BaseChatModel", FakeChatModel)
    llm_node = LlmNode(
        name="llm_node",
        llm_config=LlmConfig(name="test", model_id="test-model", api_provider="test"),
        prompt_template="irrelevant",
        outputs=[
            Property(json_schema={"title": "name", "type": "string"}),
            Property(json_schema={"title": "active", "type": "boolean"}),
        ],
    )
    fake_llm = FakeChatModel()

    executor = _node_execution.LlmNodeExecutor(llm_node, fake_llm)

    assert executor.requires_structured_generation is True
    assert fake_llm.captured_schema == {
        "title": "structured_output",
        "description": "Structured output for the LLM node.",
        "type": "object",
        "properties": {
            "name": {"title": "name", "type": "string"},
            "active": {"title": "active", "type": "boolean"},
        },
    }


@pytest.fixture()
def llm_flow() -> Flow:
    pass

    nationality_property = StringProperty(title="nationality")
    car_property = StringProperty(title="car")
    llm_config = VllmConfig(
        name="llm_config",
        model_id="openai/gpt-oss-120b",
        url=os.environ.get("OSS_API_URL"),
        default_generation_parameters=LlmGenerationConfig(temperature=0, max_tokens=512),
    )
    llm_node = LlmNode(
        name="llm_node",
        llm_config=llm_config,
        prompt_template="Answer in one short sentence. What is the fastest {{nationality}} car?",
        inputs=[nationality_property],
        outputs=[car_property],
    )
    start_node = StartNode(name="start", inputs=[nationality_property])
    end_node = EndNode(name="end", outputs=[car_property])

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, llm_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=llm_node),
            ControlFlowEdge(name="node_to_end", from_node=llm_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=nationality_property.title,
                destination_node=llm_node,
                destination_input=nationality_property.title,
            ),
            DataFlowEdge(
                name="car_edge",
                source_node=llm_node,
                source_output=car_property.title,
                destination_node=end_node,
                destination_input=car_property.title,
            ),
        ],
        outputs=[car_property],
    )
    return flow


@retry_test(max_attempts=3, wait_between_tries=2)
def test_llmnode_can_be_imported_and_executed(llm_flow: Flow) -> None:
    """
    Failure rate:          0 out of 50
    Observed on:           2026-05-11
    Average success time:  2.04 seconds per successful attempt
    Average failure time:  No time measurement
    Max attempt:           3
    Justification:         (0.02 ** 3) ~= 0.7 / 100'000
    """

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(llm_flow)
    result = agent.invoke({"inputs": {"nationality": "italian"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "car" in outputs
    assert "ital" in outputs["car"].lower()


@pytest.mark.anyio
@retry_test(max_attempts=3, wait_between_tries=2)
async def test_llmnode_can_be_executed_async(llm_flow: Flow) -> None:
    """
    Failure rate:          0 out of 50
    Observed on:           2026-05-11
    Average success time:  2.01 seconds per successful attempt
    Average failure time:  No time measurement
    Max attempt:           3
    Justification:         (0.02 ** 3) ~= 0.7 / 100'000
    """

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(llm_flow)
    result = await agent.ainvoke({"inputs": {"nationality": "italian"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "car" in outputs
    assert "ital" in outputs["car"].lower()
