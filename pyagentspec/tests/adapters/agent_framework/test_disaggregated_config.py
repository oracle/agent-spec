# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests disaggregated config loading in the Microsoft Agent Framework adapter."""
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

    serializer = AgentSpecSerializer()
    main_yaml, disag_yaml = serializer.to_yaml(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_yaml(disag_yaml, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_yaml(main_yaml, components_registry=referenced_components_runtime)
    from pyagentspec.adapters.agent_framework._types import AgentFrameworkComponent

    assert isinstance(loaded, AgentFrameworkComponent)


def test_disaggregated_loading_json_roundtrip(agent: Agent, llm: VllmConfig) -> None:

    serializer = AgentSpecSerializer()
    main_json, disag_json = serializer.to_json(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_json(disag_json, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_json(main_json, components_registry=referenced_components_runtime)
    from pyagentspec.adapters.agent_framework._types import AgentFrameworkComponent

    assert isinstance(loaded, AgentFrameworkComponent)


def test_disaggregated_loading_dict_roundtrip(agent: Agent, llm: VllmConfig) -> None:

    serializer = AgentSpecSerializer()
    main_dict, disag_dict = serializer.to_dict(
        agent,
        disaggregated_components=[(llm, "llm_config")],
        export_disaggregated_components=True,
    )

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_dict(disag_dict, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_dict(main_dict, components_registry=referenced_components_runtime)
    from pyagentspec.adapters.agent_framework._types import AgentFrameworkComponent

    assert isinstance(loaded, AgentFrameworkComponent)
