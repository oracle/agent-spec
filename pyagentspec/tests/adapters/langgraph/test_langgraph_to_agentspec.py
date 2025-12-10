# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict, cast

import pytest
from pydantic import BaseModel, SecretStr

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.nodes import BranchingNode, FlowNode
from pyagentspec.llms import OpenAiCompatibleConfig

from .conftest import get_weather

if TYPE_CHECKING:
    from pyagentspec.adapters.langgraph import AgentSpecExporter


@pytest.fixture
def agentspec_exporter() -> "AgentSpecExporter":
    from pyagentspec.adapters.langgraph import AgentSpecExporter

    return AgentSpecExporter()


def test_convert_react_agent_with_tools_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"https://{url}/v1",
    )
    agent = create_react_agent(
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
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"https://{url}/v1",
    )
    agent = create_react_agent(model=model, tools=[])
    agentspec_agent: Component = agentspec_exporter.to_component(agent)
    assert isinstance(agentspec_agent, AgentSpecAgent)
    config = agentspec_agent.llm_config
    assert isinstance(config, OpenAiCompatibleConfig)
    assert config.model_id == model_id
    assert config.url == f"https://{url}/v1"
    assert not agentspec_agent.tools


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
    assert flow.data_flow_connections and len(flow.data_flow_connections) == len(
        graph.edges
    )  # Not always true but for this case yes
    assert flow.name == assistant_name
    # TODO: assert input and output properties of the various nodes


def test_convert_graph_with_subgraph_flow_to_agentspec(
    agentspec_exporter: "AgentSpecExporter",
) -> None:
    from langgraph.graph import START, StateGraph

    class State(TypedDict):
        foo: str

    # Subgraph

    def subgraph_node_1(state: State):
        return {"foo": "hi! " + state["foo"]}

    subgraph_builder = StateGraph(State)
    subgraph_builder.add_node(subgraph_node_1)
    subgraph_builder.add_edge(START, "subgraph_node_1")
    subgraph = subgraph_builder.compile()

    # Parent graph

    builder = StateGraph(State)
    builder.add_node("node_1", subgraph)
    builder.add_edge(START, "node_1")
    assistant_name = "GraphWithSubgraph"
    compiled_graph = builder.compile(name=assistant_name)
    exporter = agentspec_exporter
    flow = exporter.to_component(compiled_graph)
    assert isinstance(flow, AgentSpecFlow)
    subflows = [node.subflow for node in flow.nodes if isinstance(node, FlowNode)]
    assert len(subflows) == 1
    subflow_nodes = [node for subflow in subflows for node in subflow.nodes]
    subflow_control_flow_edges = [
        edge for subflow in subflows for edge in subflow.control_flow_connections
    ]

    # __start__ + node_1 + __end__ + __start__ + subgraph_node1 + __end__
    assert len(flow.nodes) + len(subflow_nodes) == len(compiled_graph.nodes) + 2 + 2
    implicit_edges_to_end_nodes = 2
    assert (
        len(flow.control_flow_connections) + len(subflow_control_flow_edges)
        == len(builder.edges) + len(subgraph_builder.edges) + implicit_edges_to_end_nodes
    )
    assert flow.name == assistant_name


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
    graph.add_node(lowercase)
    graph.add_node(uppercase)
    graph.add_node(messycase)
    graph.add_conditional_edges(START, check_capitalized)

    graph_name = "Casecheck Flow"
    flow = graph.compile(name=graph_name)
    exporter = agentspec_exporter
    agentspec_flow = cast(AgentSpecFlow, exporter.to_component(flow))

    branching_node = next(
        (node for node in agentspec_flow.nodes if isinstance(node, BranchingNode)), None
    )
    langgraph_mapping = {v: v for v in {*typing.get_args(Conditionals)}}

    assert agentspec_flow.name == graph_name
    assert branching_node is not None
    assert branching_node.mapping == langgraph_mapping
    assert set(branching_node.branches) == {
        BranchingNode.DEFAULT_BRANCH,
        *typing.get_args(Conditionals),
    }
