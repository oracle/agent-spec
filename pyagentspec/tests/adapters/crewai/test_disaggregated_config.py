# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests disaggregated config loading in the AutoGen adapter."""

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

    from pyagentspec.adapters.crewai import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_yaml(disag_yaml, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_yaml(main_yaml, components_registry=referenced_components_runtime)
    from crewai import Agent

    assert isinstance(loaded, Agent)

    from pyagentspec.adapters.crewai import AgentSpecExporter

    exporter = AgentSpecExporter()
    exported_main_yaml, exported_disag_yaml = exporter.to_yaml(
        loaded,
        disaggregated_components=[(loaded.llm, "llm_config_id")],
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

    from pyagentspec.adapters.crewai import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_json(disag_json, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_json(main_json, components_registry=referenced_components_runtime)
    from crewai import Agent

    assert isinstance(loaded, Agent)

    from pyagentspec.adapters.crewai import AgentSpecExporter

    exporter = AgentSpecExporter()
    exported_main_json, exported_disag_json = exporter.to_json(
        loaded,
        disaggregated_components=[(loaded.llm, "llm_config_id")],
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

    from pyagentspec.adapters.crewai import AgentSpecLoader

    loader = AgentSpecLoader()
    referenced_components = loader.load_dict(disag_dict, import_only_referenced_components=True)
    assert "llm_config" in referenced_components

    referenced_components_runtime = {"llm_config": referenced_components["llm_config"]}

    loaded = loader.load_dict(main_dict, components_registry=referenced_components_runtime)
    from crewai import Agent

    assert isinstance(loaded, Agent)

    from pyagentspec.adapters.crewai import AgentSpecExporter

    exporter = AgentSpecExporter()
    exported_main_dict, exported_disag_dict = exporter.to_dict(
        loaded,
        disaggregated_components=[(loaded.llm, "llm_config_id")],
        export_disaggregated_components=True,
    )
    assert "component_type" in exported_main_dict
    assert exported_main_dict["component_type"] == "Agent"
    assert "llm_config" in exported_main_dict
    assert exported_main_dict["llm_config"] == {"$component_ref": "llm_config_id"}
    assert "$referenced_components" in exported_disag_dict
    assert "llm_config_id" in exported_disag_dict["$referenced_components"]
