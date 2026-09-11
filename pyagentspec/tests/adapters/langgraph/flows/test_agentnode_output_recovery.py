# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""Agent outputs are recovered from the final agent message when no structured response exists.

Covers oracle/agent-spec#224: an AgentNode whose model answered with the tool result as plain
text (instead of calling the structured output tool) returned the declared default of its
output, the list of field names ``["name", "CEO", "country"]``, instead of the values.
"""

import logging
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
from pyagentspec.adapters.langgraph._node_execution import extract_outputs_from_invoke_result
from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import OpenAiConfig
from pyagentspec.property import (
    IntegerProperty,
    ListProperty,
    Property,
    StringProperty,
)
from pyagentspec.tools import ServerTool

SEARCH_RESULTS = Property(
    json_schema={
        "title": "search_results",
        "type": "array",
        "items": {"type": "string"},
        "default": ["name", "CEO", "country"],
    }
)
QUERY = Property(json_schema={"title": "query", "type": "string", "default": ""})

PEOPLE = {"Alice": ["Alice", "No", "USA"], "Karim": ["Karim", "Yes", "Morocco"]}


def _ai_message(content: str = "", tool_calls: Any = None) -> Any:
    from langchain_core.messages import AIMessage

    return AIMessage(content=content, tool_calls=tool_calls or [])


def _fake_model(responses: List[Any]) -> Any:
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_openai import ChatOpenAI

    class FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    return FakeModel(responses=responses)


def _search_agent_flow() -> Flow:
    """Mirror of the conformance test suite's ``simple_agentnode_with_tool`` configuration."""
    search_tool = ServerTool(
        name="search_tool",
        description="This tool runs a web search with the given query and returns results",
        inputs=[QUERY],
        outputs=[SEARCH_RESULTS],
    )
    agent = Agent(
        name="Search agent",
        llm_config=OpenAiConfig(name="llm", model_id="fake-model"),
        system_prompt=(
            "Your task is to gather the required information for the user: {{query}}. "
            "Do not attempt to answer yourself, simply return the tool response."
        ),
        inputs=[QUERY],
        outputs=[SEARCH_RESULTS],
        tools=[search_tool],
    )
    start = StartNode(name="start", inputs=[QUERY])
    agent_node = AgentNode(name="Search agent node", agent=agent)
    end = EndNode(name="end", outputs=[SEARCH_RESULTS])
    return Flow(
        name="Search agent flow",
        start_node=start,
        nodes=[start, agent_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_agent", from_node=start, to_node=agent_node),
            ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="query_edge",
                source_node=start,
                source_output="query",
                destination_node=agent_node,
                destination_input="query",
            ),
            DataFlowEdge(
                name="search_results_edge",
                source_node=agent_node,
                source_output="search_results",
                destination_node=end,
                destination_input="search_results",
            ),
        ],
    )


def _run_search_flow(model_responses: List[Any], user_message: str) -> Dict[str, Any]:
    from langgraph.checkpoint.memory import MemorySaver

    calls: List[str] = []

    def get_person_info(query: str) -> List[str]:
        calls.append(query)
        return PEOPLE.get(query, [query, "Unknown", "Unknown"])

    loader = AgentSpecLoader(
        tool_registry={"search_tool": get_person_info}, checkpointer=MemorySaver()
    )
    # The AgentNode converts its agent's model when it executes, so the patch must cover the run
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=_fake_model(model_responses),
    ):
        graph = loader.load_component(_search_agent_flow())
        result = graph.invoke(
            {"inputs": {}, "messages": [{"role": "user", "content": user_message}]},
            {"configurable": {"thread_id": user_message}},
        )
    return {"outputs": result["outputs"], "tool_calls": calls}


@pytest.mark.parametrize(
    "user_message, expected_search_results",
    [
        ("Alice", ["Alice", "No", "USA"]),
        ("Karim", ["Karim", "Yes", "Morocco"]),
        ("Khalid", ["Khalid", "Unknown", "Unknown"]),
    ],
)
def test_agentnode_returns_tool_result_answered_as_plain_text(
    user_message: str, expected_search_results: List[str]
) -> None:
    # The model calls the tool, then repeats the tool result as its final plain message
    # instead of calling the structured output tool (oracle/agent-spec#224)
    import json

    responses = [
        _ai_message(
            tool_calls=[{"name": "search_tool", "args": {"query": user_message}, "id": "call_1"}]
        ),
        _ai_message(content=json.dumps(expected_search_results)),
    ]
    run = _run_search_flow(responses, user_message)
    assert run["tool_calls"] == [user_message]
    assert run["outputs"] == {"search_results": expected_search_results}


def test_agentnode_uses_structured_response_when_produced() -> None:
    responses = [
        _ai_message(tool_calls=[{"name": "search_tool", "args": {"query": "Alice"}, "id": "c1"}]),
        _ai_message(
            tool_calls=[
                {
                    "name": "AgentOutputModel",
                    "args": {"search_results": ["Alice", "No", "USA"]},
                    "id": "c2",
                }
            ]
        ),
    ]
    run = _run_search_flow(responses, "Alice")
    assert run["outputs"] == {"search_results": ["Alice", "No", "USA"]}


def test_agentnode_falls_back_to_default_when_message_cannot_be_mapped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    responses = [
        _ai_message(tool_calls=[{"name": "search_tool", "args": {"query": "Alice"}, "id": "c1"}]),
        _ai_message(content="Alice is not a CEO and lives in the USA."),
    ]
    with caplog.at_level(logging.WARNING, logger="pyagentspec.adapters.langgraph._node_execution"):
        run = _run_search_flow(responses, "Alice")
    assert run["outputs"] == {"search_results": ["name", "CEO", "country"]}
    assert "did not produce a structured response" in caplog.text
    assert "search_results" in caplog.text


# --- extract_outputs_from_invoke_result -----------------------------------------------------


def _result(messages: List[Any], **state: Any) -> Dict[str, Any]:
    return {"messages": messages, **state}


def test_structured_response_takes_precedence_over_recovered_and_default_values() -> None:
    outputs = extract_outputs_from_invoke_result(
        _result(
            [_ai_message(content='["from", "message"]')],
            structured_response={"search_results": ["x"]},
        ),
        [SEARCH_RESULTS],
    )
    assert outputs == {"search_results": ["x"]}


def test_empty_structured_response_is_treated_as_missing() -> None:
    # AgentNodeExecutor seeds the state with an empty structured_response
    outputs = extract_outputs_from_invoke_result(
        _result([_ai_message(content='["Alice", "No", "USA"]')], structured_response={}),
        [SEARCH_RESULTS],
    )
    assert outputs == {"search_results": ["Alice", "No", "USA"]}


def test_single_string_output_takes_the_final_message_text() -> None:
    answer = StringProperty(title="answer")
    outputs = extract_outputs_from_invoke_result(
        _result([_ai_message(content="The capital of France is Paris.")]), [answer]
    )
    assert outputs == {"answer": "The capital of France is Paris."}


def test_json_object_message_is_mapped_to_matching_outputs_only() -> None:
    count = IntegerProperty(title="count", default=0)
    names = ListProperty(title="names", item_type=StringProperty(title="name"))
    message = _ai_message(content='{"count": "three", "names": ["a", "b"], "other": 1}')
    outputs = extract_outputs_from_invoke_result(_result([message]), [count, names])
    # "three" is not an integer, so the declared default is kept for `count`
    assert outputs == {"count": 0, "names": ["a", "b"]}


def test_incompatible_single_value_falls_back_to_default() -> None:
    outputs = extract_outputs_from_invoke_result(
        _result([_ai_message(content='{"unrelated": true}')]), [SEARCH_RESULTS]
    )
    assert outputs == {"search_results": ["name", "CEO", "country"]}


def test_final_message_with_tool_calls_is_not_used() -> None:
    outputs = extract_outputs_from_invoke_result(
        _result(
            [
                _ai_message(
                    content='["Alice", "No", "USA"]',
                    tool_calls=[{"name": "search_tool", "args": {"query": "Alice"}, "id": "c"}],
                )
            ]
        ),
        [SEARCH_RESULTS],
    )
    assert outputs == {"search_results": ["name", "CEO", "country"]}


def test_text_content_blocks_are_joined() -> None:
    message = _ai_message(
        content=[{"type": "text", "text": '["Alice", '}, {"type": "text", "text": '"No", "USA"]'}]
    )
    outputs = extract_outputs_from_invoke_result(_result([message]), [SEARCH_RESULTS])
    assert outputs == {"search_results": ["Alice", "No", "USA"]}


def test_values_in_result_state_still_take_precedence() -> None:
    outputs = extract_outputs_from_invoke_result(
        _result([_ai_message(content='["from", "message"]')], search_results=["from", "state"]),
        [SEARCH_RESULTS],
    )
    assert outputs == {"search_results": ["from", "state"]}
