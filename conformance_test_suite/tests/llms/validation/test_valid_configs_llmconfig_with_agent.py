# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
NOTICE:
The example of OllamaConfig below requires Ollama to be installed locally. Please check https://github.com/ollama/ollama

To use Ollama:
- Download Ollama: https://ollama.com/download
- Run `ollama run llama3.2` to start your model and chat with it
  (if the llama3.2 model is not available, it will be downloaded automatically).
- Run `ollama list` to view available local llm models; you may customize your model as desired.

The default url of the Ollama server is: http://localhost:11434
"""

from pathlib import Path
from typing import Any

import pytest

from ...conftest import AgentSpecConfigLoaderType

CONFIG_DIR = Path(__file__).parent.parent / "valid_configs"

YAML_FILE_NAME_VllmConfig = "vllmconfig_with_agent.yaml"
YAML_FILE_NAME_OllamaConfig = "ollamaconfig_with_agent.yaml"
YAML_FILE_NAME_OpenAiConfig = "openaiconfig_with_agent.yaml"
YAML_FILE_NAME_OpenAiCompatibleConfig = "openaicompatibleconfig_with_agent.yaml"
YAML_FILE_NAME_OciClientConfigWithApiKey = (
    "ocigenaiconfig_with_ociclientconfigwithapikey_with_agent.yaml"
)
YAML_FILE_NAME_OciClientConfigWithInstancePrincipal = (
    "ocigenaiconfig_with_ociclientconfigwithinstanceprincipal_with_agent.yaml"
)
YAML_FILE_NAME_OciClientConfigWithResourcePrincipal = (
    "ocigenaiconfig_with_ociclientconfigwithresourceprincipal_with_agent.yaml"
)
YAML_FILE_NAME_OciClientConfigWithSecurityToken = (
    "ocigenaiconfig_with_ociclientconfigwithsecuritytoken_with_agent.yaml"
)


# List of the YAML config files to test
YAML_CONFIG_FILE_NAMES = [
    YAML_FILE_NAME_VllmConfig,
    YAML_FILE_NAME_OllamaConfig,
    YAML_FILE_NAME_OpenAiConfig,
    YAML_FILE_NAME_OpenAiCompatibleConfig,
    YAML_FILE_NAME_OciClientConfigWithApiKey,
    YAML_FILE_NAME_OciClientConfigWithInstancePrincipal,
    YAML_FILE_NAME_OciClientConfigWithResourcePrincipal,
    YAML_FILE_NAME_OciClientConfigWithSecurityToken,
]


@pytest.fixture(params=YAML_CONFIG_FILE_NAMES)
def agentspec_component(request, load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    yaml_config_file_name = request.param
    with open(CONFIG_DIR / yaml_config_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration)
    return component


def test_valid_configuration_llmconfig_with_agent_can_be_loaded(
    agentspec_component: AgentSpecConfigLoaderType,
) -> None:
    assert agentspec_component is not None, "valid file, should be loaded"
