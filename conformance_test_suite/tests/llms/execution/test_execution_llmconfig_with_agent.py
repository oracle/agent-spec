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


def assert_valid_result(result) -> None:
    # Assert at least outputs or agent_messages exists
    has_agent_messages = hasattr(result, "agent_messages")
    has_outputs = hasattr(result, "outputs")
    assert (
        has_agent_messages or has_outputs
    ), f"Result object does not look like a valid execution status: {type(result)}"
    # Assert that at least one is present and not empty
    any_not_empty = False
    if has_agent_messages:
        agent_messages = getattr(result, "agent_messages")
        if agent_messages:
            any_not_empty = True
    if has_outputs:
        outputs = getattr(result, "outputs")
        if outputs:
            any_not_empty = True
    assert any_not_empty, "Both 'agent_messages' and 'outputs' are empty or missing content."


@pytest.fixture(params=YAML_CONFIG_FILE_NAMES)
def agentspec_component(request, load_agentspec_config: AgentSpecConfigLoaderType) -> Any:
    yaml_config_file_name = request.param
    with open(CONFIG_DIR / yaml_config_file_name) as agentspec_configuration_file:
        agentspec_configuration = agentspec_configuration_file.read()
    component = load_agentspec_config(agentspec_configuration)
    return component


@pytest.mark.parametrize(
    "user_message",
    [
        ("calculate 3x6 ?"),
    ],
)
def test_llmconfig_with_agent_can_be_executed(
    agentspec_component: AgentSpecConfigLoaderType, user_message: str
) -> None:
    agentspec_component.start()
    result = agentspec_component.run()

    # Should return a valid execution status after the initial run
    assert_valid_result(result)

    # Append a user message and run again to verify no errors/exceptions
    agentspec_component.append_user_message(user_message=user_message)
    result = agentspec_component.run()

    # Should return a valid execution status after the second call
    assert_valid_result(result)
