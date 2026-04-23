# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict, cast

import pytest
from pydantic import BaseModel, SecretStr

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.nodes import AgentNode, BranchingNode, FlowNode, LlmNode, ToolNode
from pyagentspec.llms import OpenAiCompatibleConfig

from .conftest import get_weather

if TYPE_CHECKING:
    from pyagentspec.adapters.langgraph import AgentSpecExporter


@pytest.fixture
def agentspec_exporter() -> "AgentSpecExporter":
    from pyagentspec.adapters.langgraph import AgentSpecExporter

    return AgentSpecExporter()


def _property_titles(properties: list[Any] | None) -> list[str]:
    """Return the exported property titles in declaration order."""
    return [property_.title for property_ in properties or []]


def _json_schema_property_titles(property_: Any) -> list[str]:
    """Return the top-level field titles exposed by one exported property schema."""
    return list((property_.json_schema.get("properties") or {}).keys())


def _data_edge_signatures(flow: AgentSpecFlow) -> set[tuple[str, str, str, str]]:
    """Return a stable signature for each exported data edge."""
    return {
        (
            edge.source_node.name,
            edge.source_output,
            edge.destination_node.name,
            edge.destination_input,
        )
        for edge in flow.data_flow_connections or []
    }


def _find_node(flow: AgentSpecFlow, node_name: str) -> Any:
    """Return the exported node with the given name."""
    return next(node for node in flow.nodes if node.name == node_name)


def _assert_state_wired_flow(flow: AgentSpecFlow) -> None:
    """Assert that a flow falls back to opaque `state` wiring."""
    assert _property_titles(flow.inputs) == ["state"]
    assert _property_titles(flow.outputs) == ["state"]


def _assert_state_wired_nodes(flow: AgentSpecFlow, *node_names: str) -> None:
    """Assert that the named nodes expose only the opaque `state` interface."""
    for node_name in node_names:
        node = _find_node(flow, node_name)
        assert _property_titles(node.inputs) == ["state"]
        assert _property_titles(node.outputs) == ["state"]


def _assert_state_wired_edges(
    flow: AgentSpecFlow,
    edge_pairs: set[tuple[str, str]],
    extra_edges: set[tuple[str, str, str, str]] | None = None,
) -> None:
    """Assert the exported data edges for a state-wired flow."""
    expected_edges = {(source, "state", destination, "state") for source, destination in edge_pairs}
    if extra_edges is not None:
        expected_edges.update(extra_edges)
    assert _data_edge_signatures(flow) == expected_edges


def test_convert_react_agent_with_tools_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"https://{url}/v1",
    )
    agent = create_agent(
        model=model,
        tools=[
            get_weather,
        ],
    )
    agentspec_agent: Component = agentspec_exporter.to_component(agent)
    assert isinstance(agentspec_agent, AgentSpecAgent)
    config = agentspec_agent.llm_config
    assert isinstance(config, OpenAiCompatibleConfig)
    assert config.model_id == model_id
    assert config.url == f"https://{url}/v1"
    assert len(agentspec_agent.tools) == 1
    assert agentspec_agent.tools[0].name == get_weather.__name__
    assert get_weather.__doc__ is not None
    assert agentspec_agent.tools[0].description == get_weather.__doc__.strip()
    assert set([property.title for property in agentspec_agent.tools[0].inputs]) == set(
        get_weather.__code__.co_varnames[: get_weather.__code__.co_argcount]
    )


def test_convert_react_agent_without_tools_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"https://{url}/v1",
    )
    agent = create_agent(model=model, tools=[])
    agentspec_agent: Component = agentspec_exporter.to_component(agent)
    assert isinstance(agentspec_agent, AgentSpecAgent)
    config = agentspec_agent.llm_config
    assert isinstance(config, OpenAiCompatibleConfig)
    assert config.model_id == model_id
    assert config.url == f"https://{url}/v1"
    assert not agentspec_agent.tools


def test_convert_async_structured_tool_to_agentspec_server_tool(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_core.tools import StructuredTool

    from pyagentspec.tools import ServerTool as AgentSpecServerTool

    class WeatherToolArgs(BaseModel):
        city: str

    async def get_weather_async(city: str) -> str:
        return f"The weather in {city} is sunny."

    tool = StructuredTool(
        name="get_weather",
        description="Returns the weather in a certain city",
        args_schema=WeatherToolArgs,
        coroutine=get_weather_async,
    )

    agentspec_tool = agentspec_exporter.to_component(tool)

    assert isinstance(agentspec_tool, AgentSpecServerTool)
    assert agentspec_tool.name == "get_weather"
    assert agentspec_tool.description == "Returns the weather in a certain city"
    assert len(agentspec_tool.inputs) == 1
    assert agentspec_tool.inputs[0].title == "city"


def test_convert_react_agent_with_async_structured_tool_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_core.tools import StructuredTool
    from langchain_openai.chat_models import ChatOpenAI

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"https://{url}/v1",
    )

    class WeatherToolArgs(BaseModel):
        city: str

    async def get_weather_async(city: str) -> str:
        return f"The weather in {city} is sunny."

    tool = StructuredTool(
        name="get_weather",
        description="Returns the weather in a certain city",
        args_schema=WeatherToolArgs,
        coroutine=get_weather_async,
    )
    agent = create_agent(model=model, tools=[tool])

    agentspec_agent = agentspec_exporter.to_component(agent)

    assert isinstance(agentspec_agent, AgentSpecAgent)
    config = agentspec_agent.llm_config
    assert isinstance(config, OpenAiCompatibleConfig)
    assert config.model_id == model_id
    assert config.url == f"https://{url}/v1"
    assert len(agentspec_agent.tools) == 1
    assert agentspec_agent.tools[0].name == "get_weather"
    assert agentspec_agent.tools[0].description == "Returns the weather in a certain city"
    assert len(agentspec_agent.tools[0].inputs) == 1
    assert agentspec_agent.tools[0].inputs[0].title == "city"


class SchemaTypedDict(TypedDict, total=False):
    language: str
    request: str
    output: str


@dataclass
class SchemaDataClass:
    language: str
    request: str
    output: str


class SchemaPydantic(BaseModel):
    language: str
    request: str
    output: str


@pytest.mark.parametrize("schema", [SchemaTypedDict, SchemaDataClass, SchemaPydantic])
def test_convert_graph_flow_to_agentspec(
    schema: type[SchemaTypedDict] | type[SchemaDataClass] | type[SchemaPydantic],
    agentspec_exporter: "AgentSpecExporter",
) -> None:

    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    def llm_code_gen(state: SchemaTypedDict | SchemaDataClass | SchemaPydantic):
        model_id = "/storage/models/Llama-3.1-70B-Instruct"
        url = "your.url.to.llm"
        model = ChatOpenAI(
            model=model_id,
            api_key=SecretStr("EMPTY"),
            base_url=f"http://{url}/v1",
        )
        if isinstance(state, dict):
            assert "language" in state
            assert "request" in state
            return {
                "output": model.invoke(
                    f"In the {state['language']}, implement the code for {state['request']}"
                )
            }
        else:
            return {
                "output": model.invoke(
                    f"In the {state.language}, implement the code for {state.request}"
                )
            }

    graph = StateGraph(schema)
    graph.add_node("llm_code_gen", llm_code_gen)

    graph.add_edge(START, "llm_code_gen")
    graph.add_edge("llm_code_gen", END)

    assistant_name = "CodeGen Assistant"
    flow = graph.compile(name=assistant_name)
    agentspec_agent = agentspec_exporter.to_component(flow)
    assert isinstance(agentspec_agent, AgentSpecFlow)
    assert len(agentspec_agent.nodes) == len(graph.nodes) + 2  # llm_code_gen + __start__ + __end__
    assert len(agentspec_agent.control_flow_connections) == len(graph.edges)
    assert agentspec_agent.data_flow_connections and len(
        agentspec_agent.data_flow_connections
    ) == len(
        graph.edges
    )  # True for this case
    assert agentspec_agent.name == assistant_name
    inputs = agentspec_agent.inputs
    assert inputs is not None
    assert len(inputs) == 1
    assert inputs[0].title == "state"


def test_convert_graph_flow_to_agentspec_multi_schemas(
    agentspec_exporter: "AgentSpecExporter",
) -> None:

    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputSchema(TypedDict):
        city: str

    class OutputSchema(TypedDict):
        response: Any

    class InternalState(TypedDict):
        weather_data: str

    def get_weather(state: InputSchema) -> InternalState:
        """Returns the weather in a specific city.
        Args
        ----
            city: The city to check the weather for

        Returns
        -------
            weather: The weather in that city
        """
        return {"weather_data": f"The weather in {state['city']} is sunny."}

    def llm_node(state: InternalState) -> OutputSchema:
        model = ChatOpenAI(
            base_url="your.url.to.llm/v1",
            model="/storage/models/Llama-3.1-70B-Instruct",
            api_key=SecretStr("t"),
        )
        result = model.invoke(
            f"Reformulate the following sentence to the user: {state['weather_data']}"
        )
        return {"response": result.content}

    graph = StateGraph(InternalState, input_schema=InputSchema, output_schema=OutputSchema)
    graph.add_node("get_weather", get_weather)
    graph.add_node("llm_node", llm_node)
    graph.add_edge(START, "get_weather")
    graph.add_edge("get_weather", "llm_node")
    graph.add_edge("llm_node", END)
    assistant_name = "Weather Flow"
    compiled_graph = graph.compile(name=assistant_name)
    exporter = agentspec_exporter
    flow = exporter.to_component(compiled_graph)
    assert isinstance(flow, AgentSpecFlow)
    assert len(flow.nodes) == len(graph.nodes) + 2  # get_weather + llm_node + __start__ + __end__
    assert len(flow.control_flow_connections) == len(graph.edges)
    assert flow.name == assistant_name
    assert [property_.title for property_ in flow.inputs or []] == ["city"]
    assert [property_.title for property_ in flow.outputs or []] == ["response"]

    start_node = next(node for node in flow.nodes if node.name == "__start__")
    end_node = next(node for node in flow.nodes if node.name == "__end__")
    get_weather_node = next(node for node in flow.nodes if node.name == "get_weather")
    llm_node = next(node for node in flow.nodes if node.name == "llm_node")

    assert [property_.title for property_ in start_node.outputs or []] == ["city"]
    assert [property_.title for property_ in end_node.inputs or []] == ["response"]
    assert isinstance(get_weather_node, ToolNode)
    assert [property_.title for property_ in get_weather_node.inputs or []] == ["city"]
    assert [property_.title for property_ in get_weather_node.outputs or []] == ["weather_data"]
    assert isinstance(llm_node, ToolNode)
    assert [property_.title for property_ in llm_node.inputs or []] == ["weather_data"]
    assert [property_.title for property_ in llm_node.outputs or []] == ["response"]

    assert _data_edge_signatures(flow) == {
        ("__start__", "city", "get_weather", "city"),
        ("get_weather", "weather_data", "llm_node", "weather_data"),
        ("llm_node", "response", "__end__", "response"),
    }


def test_convert_graph_flow_wrapped_react_agent_node_to_agentspec_agent_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        topic: str

    class OutputState(TypedDict):
        answer: str

    class GraphState(TypedDict, total=False):
        topic: str
        answer: str

    class InternalState(TypedDict):
        messages: list[dict[str, str]]
        remaining_steps: int

    wrapped_agent = create_agent(
        model=ChatOpenAI(
            base_url="http://example.invalid/v1",
            model="openai/gpt-oss-test",
            api_key=SecretStr("t"),
        ),
        tools=[],
        state_schema=InternalState,
        system_prompt="You are helpful about {{topic}}.",
        name="subagent",
    )

    def run_agent(_agent: Any, state: InputState) -> OutputState:
        _agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": state["topic"],
                    }
                ]
            }
        )
        return {"answer": state["topic"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "call_agent",
        partial(run_agent, wrapped_agent),
        input_schema=InputState,
    )
    graph.add_edge(START, "call_agent")
    graph.add_edge("call_agent", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Agent Flow")),
    )

    assert _property_titles(flow.inputs) == ["topic"]
    assert _property_titles(flow.outputs) == ["answer"]

    start_node = _find_node(flow, "__start__")
    end_node = _find_node(flow, "__end__")
    agent_node = _find_node(flow, "call_agent")

    assert _property_titles(start_node.outputs) == ["topic"]
    assert _property_titles(end_node.inputs) == ["answer"]
    assert isinstance(agent_node, AgentNode)
    assert isinstance(agent_node.agent, AgentSpecAgent)
    assert agent_node.agent.name == "subagent"
    assert _property_titles(agent_node.inputs) == ["topic"]
    assert _property_titles(agent_node.outputs) == ["answer"]
    assert _property_titles(agent_node.agent.inputs) == ["topic"]
    assert _property_titles(agent_node.agent.outputs) == ["answer"]
    assert _data_edge_signatures(flow) == {
        ("__start__", "topic", "call_agent", "topic"),
        ("call_agent", "answer", "__end__", "answer"),
    }


def test_convert_graph_flow_wrapped_react_agent_node_falls_back_to_tool_node_on_prompt_input_mismatch(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        topic: str

    class OutputState(TypedDict):
        answer: str

    class GraphState(TypedDict, total=False):
        topic: str
        answer: str

    class InternalState(TypedDict):
        messages: list[dict[str, str]]
        remaining_steps: int

    wrapped_agent = create_agent(
        model=ChatOpenAI(
            base_url="http://example.invalid/v1",
            model="openai/gpt-oss-test",
            api_key=SecretStr("t"),
        ),
        tools=[],
        state_schema=InternalState,
        system_prompt="You are helpful.",
        name="subagent",
    )

    def run_agent(_agent: Any, state: InputState) -> OutputState:
        _agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": state["topic"],
                    }
                ]
            }
        )
        return {"answer": state["topic"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "call_agent",
        partial(run_agent, wrapped_agent),
        input_schema=InputState,
    )
    graph.add_edge(START, "call_agent")
    graph.add_edge("call_agent", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Agent Flow")),
    )
    node = _find_node(flow, "call_agent")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, AgentNode)
    assert _property_titles(node.inputs) == ["topic"]
    assert _property_titles(node.outputs) == ["answer"]


def test_convert_graph_flow_wrapped_react_agent_node_with_python_format_prompt_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        topic: str

    class OutputState(TypedDict):
        answer: str

    class GraphState(TypedDict, total=False):
        topic: str
        answer: str

    class InternalState(TypedDict):
        messages: list[dict[str, str]]
        remaining_steps: int

    wrapped_agent = create_agent(
        model=ChatOpenAI(
            base_url="http://example.invalid/v1",
            model="openai/gpt-oss-test",
            api_key=SecretStr("t"),
        ),
        tools=[],
        state_schema=InternalState,
        system_prompt="You are helpful about {topic}.",
        name="subagent",
    )

    def run_agent(_agent: Any, state: InputState) -> OutputState:
        _agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": state["topic"],
                    }
                ]
            }
        )
        return {"answer": state["topic"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "call_agent",
        partial(run_agent, wrapped_agent),
        input_schema=InputState,
    )
    graph.add_edge(START, "call_agent")
    graph.add_edge("call_agent", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(
            graph.compile(name="Wrapped Agent Flow Python Format Prompt")
        ),
    )
    node = _find_node(flow, "call_agent")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, AgentNode)
    assert _property_titles(node.inputs) == ["topic"]
    assert _property_titles(node.outputs) == ["answer"]
    assert _data_edge_signatures(flow) == {
        ("__start__", "topic", "call_agent", "topic"),
        ("call_agent", "answer", "__end__", "answer"),
    }


def test_convert_graph_flow_wrapped_react_agent_node_without_invoke_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain.agents import create_agent
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        topic: str

    class OutputState(TypedDict):
        answer: str

    class GraphState(TypedDict, total=False):
        topic: str
        answer: str

    class InternalState(TypedDict):
        messages: list[dict[str, str]]
        remaining_steps: int

    wrapped_agent = create_agent(
        model=ChatOpenAI(
            base_url="http://example.invalid/v1",
            model="openai/gpt-oss-test",
            api_key=SecretStr("t"),
        ),
        tools=[],
        state_schema=InternalState,
        system_prompt="You are helpful about {{topic}}.",
        name="subagent",
    )

    def run_agent(_agent: Any, state: InputState) -> OutputState:
        return {"answer": state["topic"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "call_agent",
        partial(run_agent, wrapped_agent),
        input_schema=InputState,
    )
    graph.add_edge(START, "call_agent")
    graph.add_edge("call_agent", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Agent Flow")),
    )
    node = _find_node(flow, "call_agent")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, AgentNode)
    assert _property_titles(node.inputs) == ["topic"]
    assert _property_titles(node.outputs) == ["answer"]


def test_convert_graph_flow_wrapped_llm_node_to_agentspec_llm_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    from pyagentspec.adapters._utils import render_template

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    prompt = "Extract structured search parameters.\nQuery: {{user_query}}"
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
        temperature=0.25,
        max_tokens=123,
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> OutputState:
        rendered_prompt = render_template(_prompt, state)
        _llm.invoke([("user", rendered_prompt)])
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Llm Flow")),
    )
    llm_node = _find_node(flow, "parse_query")

    assert isinstance(llm_node, LlmNode)
    assert _property_titles(llm_node.inputs) == ["user_query"]
    assert _property_titles(llm_node.outputs) == ["semantic_request"]
    assert llm_node.prompt_template == (
        "Extract structured search parameters.\nQuery: {{user_query}}"
    )
    assert isinstance(llm_node.llm_config, OpenAiCompatibleConfig)
    assert llm_node.llm_config.model_id == "openai/gpt-oss-test"
    assert llm_node.llm_config.url == "http://example.invalid/v1"
    assert llm_node.llm_config.default_generation_parameters is not None
    assert llm_node.llm_config.default_generation_parameters.temperature == 0.25
    assert llm_node.llm_config.default_generation_parameters.max_tokens == 123
    assert _data_edge_signatures(flow) == {
        ("__start__", "user_query", "parse_query", "user_query"),
        ("parse_query", "semantic_request", "__end__", "semantic_request"),
    }


def test_convert_graph_flow_wrapped_llm_node_with_python_format_prompt_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    prompt = "Extract structured search parameters.\nQuery: {user_query}"
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> OutputState:
        rendered_prompt = _prompt.format(user_query=state["user_query"])
        _llm.invoke([("user", rendered_prompt)])
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(
            graph.compile(name="Wrapped Llm Flow Python Format Prompt")
        ),
    )
    node = _find_node(flow, "parse_query")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, LlmNode)
    assert _property_titles(node.inputs) == ["user_query"]
    assert _property_titles(node.outputs) == ["semantic_request"]
    assert _data_edge_signatures(flow) == {
        ("__start__", "user_query", "parse_query", "user_query"),
        ("parse_query", "semantic_request", "__end__", "semantic_request"),
    }


def test_convert_graph_flow_wrapped_llm_node_without_invoke_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    prompt = "Extract structured search parameters.\nQuery: {user_query}"
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> OutputState:
        _ = _llm
        _ = _prompt
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Tool Flow No Invoke")),
    )
    node = _find_node(flow, "parse_query")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, LlmNode)
    assert _property_titles(node.inputs) == ["user_query"]
    assert _property_titles(node.outputs) == ["semantic_request"]


def test_convert_graph_flow_wrapped_llm_node_without_prompt_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any) -> OutputState:
        _llm.invoke([("user", state["user_query"])])
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node("parse_query", partial(run_llm, _llm=llm), input_schema=InputState)
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Tool Flow")),
    )
    node = _find_node(flow, "parse_query")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, LlmNode)
    assert _property_titles(node.inputs) == ["user_query"]
    assert _property_titles(node.outputs) == ["semantic_request"]


def test_convert_graph_flow_wrapped_llm_node_falls_back_to_tool_node_on_prompt_input_mismatch(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    from pyagentspec.adapters._utils import render_template

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    prompt = "Extract structured search parameters.\nQuery: {{topic}}"
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> OutputState:
        rendered_prompt = render_template(_prompt, {"topic": state["user_query"]})
        _llm.invoke([("user", rendered_prompt)])
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Llm Flow")),
    )
    node = _find_node(flow, "parse_query")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, LlmNode)
    assert _property_titles(node.inputs) == ["user_query"]
    assert _property_titles(node.outputs) == ["semantic_request"]


def test_convert_graph_flow_wrapped_llm_node_supports_static_prompt_without_inputs(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class GraphState(TypedDict, total=False):
        generated_text: str

    class OutputState(TypedDict):
        generated_text: str

    prompt = "Write a haiku about exports.\nRespond with just the poem."
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: dict[str, Any], *, _llm: Any, _prompt: Any) -> dict[str, str]:
        _ = state
        rendered_prompt = _prompt.format()
        _llm.invoke([("user", rendered_prompt)])
        return {"generated_text": "poem"}

    graph = StateGraph(
        GraphState,
        output_schema=OutputState,
    )
    graph.add_node("parse_query", partial(run_llm, _llm=llm, _prompt=prompt))
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Llm Flow Static Prompt")),
    )
    llm_node = _find_node(flow, "parse_query")

    assert isinstance(llm_node, LlmNode)
    assert _property_titles(llm_node.inputs) == []
    assert _property_titles(llm_node.outputs) == ["generated_text"]
    assert llm_node.prompt_template == "Write a haiku about exports.\nRespond with just the poem."
    assert _data_edge_signatures(flow) == {
        ("parse_query", "generated_text", "__end__", "generated_text"),
    }


def test_convert_graph_flow_wrapped_llm_node_defaults_unstructured_output_name(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    from pyagentspec.adapters._utils import render_template

    class InputState(TypedDict):
        user_query: str

    class GraphState(TypedDict, total=False):
        user_query: str
        generated_text: str

    class OutputState(TypedDict):
        generated_text: str

    prompt = "Extract structured search parameters.\nQuery: {{user_query}}"
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> dict[str, str]:
        rendered_prompt = render_template(_prompt, state)
        _llm.invoke([("user", rendered_prompt)])
        return {"generated_text": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Llm Flow Default Output")),
    )
    llm_node = _find_node(flow, "parse_query")

    assert isinstance(llm_node, LlmNode)
    assert _property_titles(llm_node.inputs) == ["user_query"]
    assert _property_titles(llm_node.outputs) == ["generated_text"]
    assert _data_edge_signatures(flow) == {
        ("__start__", "user_query", "parse_query", "user_query"),
        ("parse_query", "generated_text", "__end__", "generated_text"),
    }


def test_convert_graph_flow_wrapped_llm_node_with_chat_prompt_template_stays_tool_node(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph

    class InputState(TypedDict):
        user_query: str

    class OutputState(TypedDict):
        semantic_request: str

    class GraphState(TypedDict, total=False):
        user_query: str
        semantic_request: str

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Extract structured search parameters."),
            ("human", "Query: {user_query}"),
        ]
    )
    llm = ChatOpenAI(
        model="openai/gpt-oss-test",
        api_key=SecretStr("EMPTY"),
        base_url="http://example.invalid/v1",
    )

    def run_llm(state: InputState, *, _llm: Any, _prompt: Any) -> OutputState:
        messages = _prompt.format_messages(user_query=state["user_query"])
        _llm.invoke(messages)
        return {"semantic_request": state["user_query"]}

    graph = StateGraph(
        GraphState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    graph.add_node(
        "parse_query",
        partial(run_llm, _llm=llm, _prompt=prompt),
        input_schema=InputState,
    )
    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", END)

    flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(graph.compile(name="Wrapped Tool Flow Chat Prompt")),
    )
    node = _find_node(flow, "parse_query")

    assert isinstance(node, ToolNode)
    assert not isinstance(node, LlmNode)
    assert _property_titles(node.inputs) == ["user_query"]
    assert _property_titles(node.outputs) == ["semantic_request"]


def test_convert_graph_flow_falls_back_to_state_for_shared_state_dependency(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langgraph.graph import END, START, StateGraph

    class OutputSchema(TypedDict):
        response: str

    class InputSchema(TypedDict):
        city: str

    class SharedState(TypedDict, total=False):
        city: str
        weather_data: str
        response: str

    class WeatherPatch(TypedDict):
        weather_data: str

    class FormatterInput(TypedDict):
        city: str
        weather_data: str

    def patch_weather(state: InputSchema) -> WeatherPatch:
        return {"weather_data": f"The weather in {state['city']} is sunny."}

    def format_with_city(state: FormatterInput) -> OutputSchema:
        return {"response": f"{state['city']}: {state['weather_data']}"}

    shared_state_graph = StateGraph(
        SharedState,
        input_schema=InputSchema,
        output_schema=OutputSchema,
    )
    shared_state_graph.add_node("get_weather", patch_weather)
    shared_state_graph.add_node("format_weather", format_with_city)
    shared_state_graph.add_edge(START, "get_weather")
    shared_state_graph.add_edge("get_weather", "format_weather")
    shared_state_graph.add_edge("format_weather", END)

    shared_state_flow = cast(
        AgentSpecFlow,
        agentspec_exporter.to_component(shared_state_graph.compile(name="Shared State Flow")),
    )
    _assert_state_wired_flow(shared_state_flow)
    assert shared_state_flow.inputs is not None
    assert shared_state_flow.outputs is not None
    assert _json_schema_property_titles(shared_state_flow.inputs[0]) == ["city"]
    assert _json_schema_property_titles(shared_state_flow.outputs[0]) == ["response"]
    _assert_state_wired_nodes(
        shared_state_flow,
        "__start__",
        "get_weather",
        "format_weather",
        "__end__",
    )
    start_node = _find_node(shared_state_flow, "__start__")
    end_node = _find_node(shared_state_flow, "__end__")
    assert start_node.outputs is not None
    assert end_node.inputs is not None
    assert _json_schema_property_titles(start_node.outputs[0]) == ["city"]
    assert _json_schema_property_titles(end_node.inputs[0]) == ["response"]
    _assert_state_wired_edges(
        shared_state_flow,
        {
            ("__start__", "get_weather"),
            ("get_weather", "format_weather"),
            ("format_weather", "__end__"),
        },
    )


def test_convert_graph_with_subgraph_flow_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langgraph.graph import END, START, StateGraph

    class ParentState(TypedDict, total=False):
        foo: str
        bar: str

    class ParentInput(TypedDict):
        foo: str

    class ParentOutput(TypedDict):
        bar: str

    class SubgraphState(TypedDict, total=False):
        foo: str
        bar: str

    class SubgraphInput(TypedDict):
        foo: str

    class SubgraphOutput(TypedDict):
        bar: str

    def subgraph_node_1(state: SubgraphInput) -> SubgraphOutput:
        return {"bar": "hi! " + state["foo"]}

    # Keep both parent and subgraph field-addressable so this test covers nested subgraph export
    # on the direct field-wiring path, not the separate opaque `state` fallback behavior.
    subgraph_builder = StateGraph(
        SubgraphState,
        input_schema=SubgraphInput,
        output_schema=SubgraphOutput,
    )
    subgraph_builder.add_node("subgraph_node_1", subgraph_node_1)
    subgraph_builder.add_edge(START, "subgraph_node_1")
    subgraph_builder.add_edge("subgraph_node_1", END)
    subgraph = subgraph_builder.compile()

    builder = StateGraph(
        ParentState,
        input_schema=ParentInput,
        output_schema=ParentOutput,
    )
    builder.add_node("node_1", subgraph)
    builder.add_edge(START, "node_1")
    builder.add_edge("node_1", END)
    assistant_name = "GraphWithSubgraph"
    compiled_graph = builder.compile(name=assistant_name)
    exporter = agentspec_exporter
    flow = cast(AgentSpecFlow, exporter.to_component(compiled_graph))
    assert isinstance(flow, AgentSpecFlow)
    assert flow.name == assistant_name
    assert _property_titles(flow.inputs) == ["foo"]
    assert _property_titles(flow.outputs) == ["bar"]

    start_node = _find_node(flow, "__start__")
    end_node = _find_node(flow, "__end__")
    flow_node = _find_node(flow, "node_1")
    assert isinstance(flow_node, FlowNode)
    assert _property_titles(start_node.outputs) == ["foo"]
    assert _property_titles(end_node.inputs) == ["bar"]
    assert _property_titles(flow_node.inputs) == ["foo"]
    assert _property_titles(flow_node.outputs) == ["bar"]
    assert _data_edge_signatures(flow) == {
        ("__start__", "foo", "node_1", "foo"),
        ("node_1", "bar", "__end__", "bar"),
    }

    subflow = flow_node.subflow
    assert _property_titles(subflow.inputs) == ["foo"]
    assert _property_titles(subflow.outputs) == ["bar"]
    subflow_start_node = _find_node(subflow, "__start__")
    subflow_end_node = _find_node(subflow, "__end__")
    subgraph_node = _find_node(subflow, "subgraph_node_1")
    assert _property_titles(subflow_start_node.outputs) == ["foo"]
    assert _property_titles(subflow_end_node.inputs) == ["bar"]
    assert _property_titles(subgraph_node.inputs) == ["foo"]
    assert _property_titles(subgraph_node.outputs) == ["bar"]
    assert _data_edge_signatures(subflow) == {
        ("__start__", "foo", "subgraph_node_1", "foo"),
        ("subgraph_node_1", "bar", "__end__", "bar"),
    }


Conditionals: TypeAlias = Literal["lowercase", "uppercase", "messycase"]


def test_conditional_graph(agentspec_exporter: "AgentSpecExporter") -> None:
    from langgraph.graph import START, StateGraph

    class InputSchema(TypedDict):
        sentence: str

    class OutputSchema(TypedDict):
        response: Any

    class InternalState(TypedDict):
        sentence: str

    def check_capitalized(state: InternalState) -> Conditionals:
        if state["sentence"].lower() == state["sentence"]:
            return "lowercase"
        elif state["sentence"].upper() == state["sentence"]:
            return "uppercase"
        else:
            return "messycase"

    def lowercase(state: InternalState) -> OutputSchema:
        return {"response": "The sentence you gave me is lowercase."}

    def uppercase(state: InternalState) -> OutputSchema:
        return {"response": "The sentence you gave me is uppercase."}

    def messycase(state: InternalState) -> OutputSchema:
        return {"response": "The sentence you gave me is messy."}

    graph = StateGraph(InternalState, input_schema=InputSchema, output_schema=OutputSchema)
    graph.add_node("lowercase_node", lowercase)
    graph.add_node("uppercase_node", uppercase)
    graph.add_node("messycase_node", messycase)
    graph.add_conditional_edges(
        START,
        check_capitalized,
        {
            "lowercase": "lowercase_node",
            "uppercase": "uppercase_node",
            "messycase": "messycase_node",
        },
    )

    graph_name = "Casecheck Flow"
    flow = graph.compile(name=graph_name)
    agentspec_flow = cast(AgentSpecFlow, agentspec_exporter.to_component(flow))

    branching_node = next(
        (node for node in agentspec_flow.nodes if isinstance(node, BranchingNode)), None
    )
    branch_edges = {
        (
            edge.to_node.name,
            edge.from_branch,
        )
        for edge in agentspec_flow.control_flow_connections
        if edge.from_node is branching_node
    }

    assert agentspec_flow.name == graph_name
    assert branching_node is not None
    assert branching_node.mapping == {
        "lowercase": "lowercase_node",
        "uppercase": "uppercase_node",
        "messycase": "messycase_node",
    }
    assert set(branching_node.branches) == {
        BranchingNode.DEFAULT_BRANCH,
        "lowercase_node",
        "uppercase_node",
        "messycase_node",
    }
    # Compare `(destination node name, from_branch)` pairs. BranchingNode branches are the mapped
    # target names in Agent Spec, so the non-default branch labels match their destination nodes.
    assert branch_edges == {
        ("lowercase_node", "lowercase_node"),
        ("uppercase_node", "uppercase_node"),
        ("messycase_node", "messycase_node"),
        ("__end__", BranchingNode.DEFAULT_BRANCH),
    }
