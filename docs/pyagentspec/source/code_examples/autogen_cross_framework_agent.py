# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
# mypy: ignore-errors

import os
from pathlib import Path

CONFIGS_DIR = Path(os.path.dirname(__file__)).parent / "agentspec_config_examples"

# .. define-tool-registry:
from typing import List


def hello_world() -> None:
    """Prints 'Hello world!'"""
    print("Hello world!")
    return None


def rag_tool(query: str) -> List[str]:
    """Search and return the list of results"""
    return ["result 1", "result 2"]


tool_registry = {
    "rag_tool": rag_tool,
    "hello_world_tool": hello_world,
}
# .. end-define-tool-registry:

# .. agentspec-deserialization:
from pyagentspec.serialization import AgentSpecDeserializer

with open(CONFIGS_DIR / "simple_agent_with_rag_tool.json", "r") as file:
    assistant_json = file.read()

deserializer = AgentSpecDeserializer()
deserialized_agentspec_agent = deserializer.from_json(assistant_json)
# .. end-agentspec-deserialization:

# .. define-llm:
from autogen_ext.models.openai import OpenAIChatCompletionClient

from pyagentspec.llms import LlmConfig, VllmConfig


def convert_agentspec_llm_to_autogen(agentspec_llm: LlmConfig):
    if isinstance(agentspec_llm, VllmConfig):
        return OpenAIChatCompletionClient(
            model=agentspec_llm.model_id,
            base_url=f"http://{agentspec_llm.url}/v1",
            api_key="",
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
            },
        )
    # Here we should write the translation for
    # the other types of LLM that are available in Agent Spec


# .. end-define-llm:


# .. define-tools:
from autogen_core.tools import FunctionTool

from pyagentspec.tools import ServerTool, Tool


def convert_agentspec_tool_to_autogen(agentspec_tool: Tool):
    if isinstance(agentspec_tool, ServerTool):
        return FunctionTool(
            tool_registry[agentspec_tool.name],
            name=agentspec_tool.name,
            description=agentspec_tool.description,
        )
    # Here we should write the translation for
    # the other types of Tool that are available in Agent Spec


# .. end-define-tools:


# .. define-agent:
from autogen_agentchat.agents import AssistantAgent

from pyagentspec.agent import Agent


def convert_agentspec_agent_to_autogen(agentspec_agent: Agent):
    return AssistantAgent(
        name=agentspec_agent.name,
        description=agentspec_agent.description,
        system_message=agentspec_agent.system_prompt,
        model_client=convert_agentspec_llm_to_autogen(agentspec_agent.llm_config),
        tools=[convert_agentspec_tool_to_autogen(tool) for tool in agentspec_agent.tools],
    )


# .. end-define-agent:


# .. define-conversion:
from pyagentspec import Component


def convert_agentspec_to_autogen(agentspec_component: Component):
    if isinstance(agentspec_component, LlmConfig):
        return convert_agentspec_llm_to_autogen(agentspec_component)
    elif isinstance(agentspec_component, Tool):
        return convert_agentspec_tool_to_autogen(agentspec_component)
    elif isinstance(agentspec_component, Agent):
        return convert_agentspec_agent_to_autogen(agentspec_component)
    # Here we should write the translation for
    # the other components that are available in Agent Spec


# The agent's system prompt contains an input placeholder
# We fill it with the desired domain of expertise, i.e., computer science
deserialized_agentspec_agent.system_prompt = deserialized_agentspec_agent.system_prompt.replace(
    "{{domain_of_expertise}}", "computer science"
)

agent = convert_agentspec_to_autogen(deserialized_agentspec_agent)
# .. end-define-conversion:
