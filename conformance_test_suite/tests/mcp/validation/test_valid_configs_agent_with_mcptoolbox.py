# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"
YAML_FILE_NAME = "agent_with_1_mcptoolbox.yaml"


@pytest.fixture
def agentspec_component_fixture(load_agentspec_config: AgentSpecConfigLoaderType):

    with open(CONFIG_DIR / YAML_FILE_NAME) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    agentspec_component = load_agentspec_config(agentspec_configuration)
    return agentspec_component


def test_valid_agent_configuration_with_mcptoolbox_can_be_loaded(
    agentspec_component_fixture,
) -> None:
    assert agentspec_component_fixture is not None, "valid file, should be loaded"
