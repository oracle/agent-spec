# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecSerializer


def test_disaggregated_loading_yaml_roundtrip() -> None:
    # Build a minimal Agent with a VLLM config (safe to instantiate without network)
    llm = VllmConfig(name="llm-dev", model_id="llama3.1-8b-instruct", url="http://dummy.llm")
    agent = Agent(
        id="agent_id",
        name="Weather Agent",
        llm_config=llm,
        system_prompt="You are a helpful assistant.",
        tools=[],
    )

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

    # Registry should include our custom id mapped to an Agent Spec component
    assert "llm_config" in referenced_components
    from pyagentspec.llms.llmconfig import LlmConfig

    assert isinstance(referenced_components["llm_config"], LlmConfig)

    # Optionally, swap the LLM dynamically before loading main
    new_llm = VllmConfig(name="llm-prod", model_id="llama3.1-70b-instruct", url="http://prod.llm")
    referenced_components["llm_config"] = new_llm

    # Load the main component using the updated registry
    compiled = loader.load_yaml(main_yaml, components_registry=referenced_components)

    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)


def test_disaggregated_loading_json_roundtrip() -> None:
    llm = VllmConfig(name="llm-dev", model_id="llama3.1-8b-instruct", url="http://dummy.llm")
    agent = Agent(
        id="agent_id",
        name="Weather Agent",
        llm_config=llm,
        system_prompt="You are a helpful assistant.",
        tools=[],
    )

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
    from pyagentspec.llms.llmconfig import LlmConfig

    assert isinstance(referenced_components["llm_config"], LlmConfig)

    compiled = loader.load_json(main_json, components_registry=referenced_components)
    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)


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

    # Ensure both IDs are present and are Agent Spec components
    assert set(registry) == {"llm_config", "server_weather_tool"}
    from pyagentspec.llms.llmconfig import LlmConfig
    from pyagentspec.tools import ServerTool as AgentSpecServerTool

    assert isinstance(registry["llm_config"], LlmConfig)
    assert isinstance(registry["server_weather_tool"], AgentSpecServerTool)

    compiled = loader.load_yaml(main_yaml, components_registry=registry)
    from pyagentspec.adapters.langgraph._types import CompiledStateGraph

    assert isinstance(compiled, CompiledStateGraph)


def _get_weather_impl(city: str) -> str:  # matches the tool name above
    return f"The weather in {city} is sunny."
