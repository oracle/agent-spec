# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecSerializer


@pytest.fixture
def llm() -> VllmConfig:
    return VllmConfig(name="llm-dev", model_id="llama3.1-8b-instruct", url="http://dummy.llm")


@pytest.fixture
def agent(llm: VllmConfig) -> Agent:
    return Agent(
        id="agent_id",
        name="Weather Agent",
        llm_config=llm,
        system_prompt="You are a helpful assistant.",
        tools=[],
    )


def test_disaggregated_loading_yaml_roundtrip(agent: Agent, llm: VllmConfig) -> None:

    # Serialize with disaggregation (LLM config)
    serializer = AgentSpecSerializer()
    main_yaml, disag_yaml = serializer.to_yaml(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    # Load with the LangGraph adapter in two phases
    from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphLoader

    loader = LangGraphLoader()
    referenced_components = loader.load_yaml(disag_yaml, import_only_referenced_components=True)

    # Registry should include our custom id mapped to a LangGraph component (BaseChatModel)
    assert "llm_config" in referenced_components
    from pyagentspec.adapters.langgraph._types import BaseChatModel

    assert isinstance(referenced_components["llm_config"], BaseChatModel)

    # Optionally, swap the LLM dynamically before loading main (Agent Spec component is accepted)
    new_llm = VllmConfig(name="llm-prod", model_id="llama3.1-70b-instruct", url="http://prod.llm")
    referenced_components["llm_config"] = new_llm

    # Load the main component using the updated registry
    compiled = loader.load_yaml(main_yaml, components_registry=referenced_components)

    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)

    from pyagentspec.adapters.langgraph import AgentSpecExporter
    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter

    model_node = compiled.builder.nodes["model"]
    chat_model = LangGraphToAgentSpecConverter()._extract_basechatmodel_from_model_node(model_node)
    exporter = AgentSpecExporter()
    exported_main_yaml, exported_disag_yaml = exporter.to_yaml(
        compiled,
        disaggregated_components=[(chat_model, "llm_config_id")],
        export_disaggregated_components=True,
    )
    assert "component_type" in exported_main_yaml
    assert "Agent" in exported_main_yaml
    assert "llm_config_id" in exported_main_yaml
    assert "$referenced_components" in exported_disag_yaml
    assert "llm_config_id" in exported_disag_yaml


def test_disaggregated_loading_json_roundtrip(agent: Agent, llm: VllmConfig) -> None:

    serializer = AgentSpecSerializer()
    main_json, disag_json = serializer.to_json(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphLoader

    loader = LangGraphLoader()
    referenced_components = loader.load_json(disag_json, import_only_referenced_components=True)

    assert "llm_config" in referenced_components
    from pyagentspec.adapters.langgraph._types import BaseChatModel

    assert isinstance(referenced_components["llm_config"], BaseChatModel)

    compiled = loader.load_json(main_json, components_registry=referenced_components)
    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)

    from pyagentspec.adapters.langgraph import AgentSpecExporter
    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter

    model_node = compiled.builder.nodes["model"]
    chat_model = LangGraphToAgentSpecConverter()._extract_basechatmodel_from_model_node(model_node)
    exporter = AgentSpecExporter()
    exported_main_json, exported_disag_json = exporter.to_json(
        compiled,
        disaggregated_components=[(chat_model, "llm_config_id")],
        export_disaggregated_components=True,
    )
    assert "component_type" in exported_main_json
    assert "Agent" in exported_main_json
    assert "llm_config_id" in exported_main_json
    assert "$referenced_components" in exported_disag_json
    assert "llm_config_id" in exported_disag_json


def test_disaggregated_loading_dict_roundtrip(agent: Agent, llm: VllmConfig) -> None:

    serializer = AgentSpecSerializer()
    main_dict, disag_dict = serializer.to_dict(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphLoader

    loader = LangGraphLoader()
    referenced_components = loader.load_dict(disag_dict, import_only_referenced_components=True)

    assert "llm_config" in referenced_components
    from pyagentspec.adapters.langgraph._types import BaseChatModel

    assert isinstance(referenced_components["llm_config"], BaseChatModel)

    compiled = loader.load_dict(main_dict, components_registry=referenced_components)
    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)

    from pyagentspec.adapters.langgraph import AgentSpecExporter
    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter

    model_node = compiled.builder.nodes["model"]
    chat_model = LangGraphToAgentSpecConverter()._extract_basechatmodel_from_model_node(model_node)
    exporter = AgentSpecExporter()
    exported_main_dict, exported_disag_dict = exporter.to_dict(
        compiled,
        disaggregated_components=[(chat_model, "llm_config_id")],
        export_disaggregated_components=True,
    )
    assert "component_type" in exported_main_dict
    assert exported_main_dict["component_type"] == "Agent"
    assert "llm_config" in exported_main_dict
    assert exported_main_dict["llm_config"] == {"$component_ref": "llm_config_id"}
    assert "$referenced_components" in exported_disag_dict
    assert "llm_config_id" in exported_disag_dict["$referenced_components"]


def test_disaggregated_tool_and_llm_can_load_with_registry() -> None:
    # Define an LLM and a server tool, then disaggregate both
    from pyagentspec.property import StringProperty
    from pyagentspec.tools import ServerTool

    city_input = StringProperty(title="city", default="zurich")
    weather_output = StringProperty(title="forecast")

    tool = ServerTool(
        id="weather_tool",
        name="get_weather",
        description="Gets the weather for a city",
        inputs=[city_input],
        outputs=[weather_output],
    )

    llm = VllmConfig(name="llm-dev", model_id="llama3.1-8b-instruct", url="http://dummy.llm")
    agent = Agent(
        id="agent_id",
        name="Weather Agent",
        llm_config=llm,
        system_prompt="You are a helpful assistant.",
        tools=[tool],
    )

    serializer = AgentSpecSerializer()
    main_yaml, disag_yaml = serializer.to_yaml(
        agent,
        disaggregated_components=[(llm, "llm_config"), (tool, "server_weather_tool")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphLoader

    loader = LangGraphLoader(tool_registry={"get_weather": _get_weather_impl})
    registry = loader.load_yaml(disag_yaml, import_only_referenced_components=True)

    # Ensure both IDs are present and converted to LangGraph components
    assert set(registry) == {"llm_config", "server_weather_tool"}
    from pyagentspec.adapters.langgraph._types import BaseChatModel, StructuredTool

    assert isinstance(registry["llm_config"], BaseChatModel)
    assert isinstance(registry["server_weather_tool"], StructuredTool)

    compiled = loader.load_yaml(main_yaml, components_registry=registry)
    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)


def _get_weather_impl(city: str) -> str:  # matches the tool name above
    return f"The weather in {city} is sunny."
