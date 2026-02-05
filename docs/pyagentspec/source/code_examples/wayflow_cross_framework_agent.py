# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

import os
from pathlib import Path

CONFIGS_DIR = Path(os.path.dirname(__file__)).parent / "agentspec_config_examples"

# OciClientConfigWithUserAuthentication removed from PyAgentSpec
# but not in wayflowcore
exit()

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
from wayflowcore.models import VllmModel

from pyagentspec.llms import LlmConfig, VllmConfig


def convert_agentspec_llm_to_wayflow(agentspec_llm: LlmConfig):
    if isinstance(agentspec_llm, VllmConfig):
        return VllmModel(
            model_id=agentspec_llm.model_id,
            host_port=agentspec_llm.url,
        )
    # Here we should write the translation for
    # the other types of LLM that are available in Agent Spec


# .. end-define-llm:


# .. define-tools:
from wayflowcore.property import Property
from wayflowcore.tools import ServerTool as WayflowServerTool

from pyagentspec.tools import ServerTool, Tool


def convert_agentspec_tool_to_wayflow(agentspec_tool: Tool):
    if isinstance(agentspec_tool, ServerTool):
        return WayflowServerTool(
            func=tool_registry[agentspec_tool.name],
            name=agentspec_tool.name,
            description=agentspec_tool.description,
            input_descriptors=[
                Property.from_json_schema(input_.json_schema) for input_ in agentspec_tool.inputs
            ],
            output_descriptors=[
                Property.from_json_schema(output.json_schema) for output in agentspec_tool.outputs
            ],
        )


# .. end-define-tools:


# .. define-agent:
from wayflowcore.agent import Agent as WayflowAgent

from pyagentspec.agent import Agent


def convert_agentspec_agent_to_wayflow(agentspec_agent: Agent):
    return WayflowAgent(
        llm=convert_agentspec_llm_to_wayflow(agentspec_agent.llm_config),
        custom_instruction=agentspec_agent.system_prompt,
        tools=[convert_agentspec_tool_to_wayflow(tool) for tool in agentspec_agent.tools],
    )


# .. end-define-agent:


# .. define-conversion:
from pyagentspec import Component


def convert_agentspec_to_wayflow(agentspec_component: Component):
    if isinstance(agentspec_component, LlmConfig):
        return convert_agentspec_llm_to_wayflow(agentspec_component)
    elif isinstance(agentspec_component, Tool):
        return convert_agentspec_tool_to_wayflow(agentspec_component)
    elif isinstance(agentspec_component, Agent):
        return convert_agentspec_agent_to_wayflow(agentspec_component)
    # Here we should write the translation for
    # the other components that are available in Agent Spec


agent = convert_agentspec_to_wayflow(deserialized_agentspec_agent)
# .. end-define-conversion:

# .. start-conversation
# We fill the input of the Agent when we start the conversation
conversation = agent.start_conversation(inputs={"domain_of_expertise": "computer science"})
status = conversation.execute()
# .. end-conversation

# .. using-langgraph-agentspec-adapter:
# Load the Agent Spec component into a LangGraph assistant
from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphLoader

loader = LangGraphLoader(tool_registry=tool_registry)
agent = loader.load_component(deserialized_agentspec_agent)
# .. end-using-langgraph-agentspec-adapter:
# .. using-crewai-agentspec-adapter:
# Load the Agent Spec component into a CrewAI assistant
from pyagentspec.adapters.crewai import AgentSpecLoader as CrewAILoader

loader = CrewAILoader(tool_registry=tool_registry)
agent = loader.load_component(deserialized_agentspec_agent)
# .. end-using-crewai-agentspec-adapter:
# .. using-autogen-agentspec-adapter:
# Load the Agent Spec component into a AutoGen assistant
from pyagentspec.adapters.autogen import AgentSpecLoader as AutoGenLoader

loader = AutoGenLoader(tool_registry=tool_registry)
agent = loader.load_component(deserialized_agentspec_agent)
# .. end-using-autogen-agentspec-adapter:
# .. using-wayflow-agentspec-adapter:
from wayflowcore.agentspec import AgentSpecLoader as WayFlowLoader

loader = WayFlowLoader(tool_registry=tool_registry)
agent = loader.load_component(deserialized_agentspec_agent)
# .. end-using-wayflow-agentspec-adapter:

# .. start-full-code
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


from pyagentspec.serialization import AgentSpecDeserializer

with open(CONFIGS_DIR / "simple_agent_with_rag_tool.json", "r") as file:
    assistant_json = file.read()

deserializer = AgentSpecDeserializer()
deserialized_agentspec_agent = deserializer.from_json(assistant_json)


from wayflowcore.models import VllmModel

from pyagentspec.llms import LlmConfig, VllmConfig


def convert_agentspec_llm_to_wayflow(agentspec_llm: LlmConfig):
    if isinstance(agentspec_llm, VllmConfig):
        return VllmModel(
            model_id=agentspec_llm.model_id,
            host_port=agentspec_llm.url,
        )
    # Here we should write the translation for
    # the other types of LLM that are available in Agent Spec


from wayflowcore.property import Property
from wayflowcore.tools import ServerTool as WayflowServerTool

from pyagentspec.tools import ServerTool, Tool


def convert_agentspec_tool_to_wayflow(agentspec_tool: Tool):
    if isinstance(agentspec_tool, ServerTool):
        return WayflowServerTool(
            func=tool_registry[agentspec_tool.name],
            name=agentspec_tool.name,
            description=agentspec_tool.description,
            input_descriptors=[
                Property.from_json_schema(input_.json_schema) for input_ in agentspec_tool.inputs
            ],
            output_descriptors=[
                Property.from_json_schema(output.json_schema) for output in agentspec_tool.outputs
            ],
        )


from wayflowcore.agent import Agent as WayflowAgent

from pyagentspec.agent import Agent


def convert_agentspec_agent_to_wayflow(agentspec_agent: Agent):
    return WayflowAgent(
        llm=convert_agentspec_llm_to_wayflow(agentspec_agent.llm_config),
        custom_instruction=agentspec_agent.system_prompt,
        tools=[convert_agentspec_tool_to_wayflow(tool) for tool in agentspec_agent.tools],
    )


from pyagentspec import Component


def convert_agentspec_to_wayflow(agentspec_component: Component):
    if isinstance(agentspec_component, LlmConfig):
        return convert_agentspec_llm_to_wayflow(agentspec_component)
    elif isinstance(agentspec_component, Tool):
        return convert_agentspec_tool_to_wayflow(agentspec_component)
    elif isinstance(agentspec_component, Agent):
        return convert_agentspec_agent_to_wayflow(agentspec_component)
    # Here we should write the translation for
    # the other components that are available in Agent Spec


agent = convert_agentspec_to_wayflow(deserialized_agentspec_agent)
conversation = agent.start_conversation(inputs={"domain_of_expertise": "computer science"})
status = conversation.execute()


from wayflowcore.agentspec import AgentSpecLoader
from wayflowcore.tools import tool

loader = AgentSpecLoader(
    tool_registry={
        tool_name: tool(tool_function, description_mode="only_docstring")
        for tool_name, tool_function in tool_registry.items()
    }
)
agent = loader.load_component(deserialized_agentspec_agent)
# .. end-full-code
