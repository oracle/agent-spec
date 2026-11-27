# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path
from unittest.mock import Mock

import pytest
from agentspec_cts_sdk import AgentSpecRunnableComponent

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "agent_with_2_tools_confirmation.yaml"


def _create_tools_with_spy(spy: Mock):
    def multiplication_tool(a, b):
        spy("product", a, b)
        return {"product": a * b}

    def summation_tool(a, b):
        spy("sum", a, b)
        return {"sum": a + b}

    return multiplication_tool, summation_tool


@pytest.fixture
def agentspec_component(
    load_agentspec_config: AgentSpecConfigLoaderType, tool_calling_spy
) -> AgentSpecRunnableComponent:
    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    multiplication_tool, summation_tool = _create_tools_with_spy(tool_calling_spy)
    tool_registry = {
        "multiplication_tool": multiplication_tool,
        "summation_tool": summation_tool,
    }
    component = load_agentspec_config(agentspec_configuration, tool_registry=tool_registry)
    return component


def test_valid_configuration_agent_with_2_tools_can_be_loaded(agentspec_component) -> None:
    assert agentspec_component is not None, "Valid file, should be loaded"
