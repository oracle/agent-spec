# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyagentspec[langgraph]==26.1.0",
#   "wayflowcore==26.1.0",
# ]
# ///

import os
from pathlib import Path
from typing import cast

from pyagentspec.agent import Agent
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig

llm_config = OpenAiCompatibleConfig(
    name="gpt-oss-120b",
    model_id="openai/gpt-oss-120b",
    url=os.environ["OSS_API_URL"],
)
llms_context = Path("generated-llms.txt").read_text()

AGENT_SPEC_CODE_GENERATION_PROMPT = """
# ROLE

You are an expert at generating Agent Spec configurations. You will be given the context of the Agent Spec python framework, and your task is to generate python code that fulfills the requirements of the user prompt.

# Agent Spec: Complete Guide for LLM-Assisted Configuration Creation

## Introduction

Agent Spec is a portable, platform-agnostic configuration language for defining agentic systems. It supports creating standalone agents and structured workflows (flows) composed of connected nodes. The Python pyagentspec SDK allows programmatic creation of components that can be serialized to JSON/YAML.

Key components:
- **Agent**: Conversational LLM-powered assistants with tools
- **Flow**: Structured workflows with nodes and edges
- **Tool**: Functions available to agents (server/client/remote)
- **Property**: Input/output schemas with JSON Schema validation
- **Node**: Flow building blocks (StartNode, EndNode, LlmNode, AgentNode, ToolNode, BranchingNode, etc.)
- **Edge**: Control flow and data flow connections between nodes

## Full API Reference

{{llms_context}}

## Common Patterns

- **Tool-augmented Agents**: Combine agents with ServerTools for autonomous capabilities
- **LLM Chains**: Use LlmNode sequences for multi-step reasoning
- **Conditional Workflows**: BranchingNode + different paths for decision trees
- **Agent Coordination**: Multiple AgentNodes in a flow for specialized tasks
- **Nested Flows**: FlowNode for hierarchical workflow organization

## Best Practices
1. **Property Inference**: Let pyagentspec infer inputs/outputs when possible from templates and agent definitions
2. **Branching**: Always include a "default" branch in BranchingNode mappings
3. **Human-in-the-Loop**: Set `human_in_the_loop=True` when agents need user approval for actions
4. **Serialization**: JSON is preferred to YAML when exporting a pyagentspec assistant, using the AgentSpecSerializer class

## Generated code structure

The code that you generate should be concise, avoid comments as much as possible, and avoid verbosely explaining the generated code.
If there's a section of the code that needs more explaining, you can instead define functions that are well named, containing docstrings that explain what the function creates.

## Important additions to the generated code
At the end of the generated code you should:
- Add a main function that serializes the code into JSON/YAML

- Pay attention to imports, if you have a file named: pyagentspec/tools/servertool.py, you should at the very least import the ServerTool class this way: `from pyagentspec.tools.servertool import ServerTool`, unless there is an example that showcases a better way to import the class. DO NOT import everything with a plain `from pyagentspec`.

- Add the following function to allow the user to validate the generated configuration.
<validation_function>
from pydantic import BaseModel, model_validator
from pyagentspec.validation_helpers import PyAgentSpecErrorDetails


class Json(BaseModel):
    value: str

    @model_validator(mode="after")
    def _validate_json(self) -> "Json":
        import json

        json.loads(self.value)
        return self


class Yaml(BaseModel):
    value: str

    @model_validator(mode="after")
    def _validate_yaml(self) -> "Yaml":
        import yaml

        yaml.safe_load(self.value)
        return self


def validate_agent_spec_configuration(config: Json | Yaml) -> list[PyAgentSpecErrorDetails]:
    from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer

    serializer = AgentSpecSerializer()
    deserializer = AgentSpecDeserializer()

    match config:
        case Json(value=value):
            component = deserializer.from_json(value)
        case Yaml(value=value):
            component = deserializer.from_yaml(value)
    dictionary = serializer.to_dict(component)
    _, errors = deserializer.from_partial_dict(dictionary)
    return errors
</validation_function>

This guide provides the foundation for creating any Agent Spec configuration using the pyagentspec SDK.
"""

agent = Agent(
    name="Agent Spec Codegen",
    llm_config=llm_config,
    system_prompt=AGENT_SPEC_CODE_GENERATION_PROMPT,
)

queries = [
    "Build a simple Agent with one tool",
    "Build a simple Flow that runs a tool and calls an LLM",
    "Build a Flow that given a user query to generate code, first generates the code with an LLM, then evaluates its quality with another LLM, and either returns the code directly if passing or improves the code (1 pass only, no looping)",
]


def run_agent_with_wayflow(scenario: str, scenario_number: int) -> None:
    from wayflowcore import Agent as WayFlowAgent
    from wayflowcore.agentspec import AgentSpecLoader

    loader = AgentSpecLoader()
    wayflow_agent = cast(WayFlowAgent, loader.load_component(agent))
    conversation = wayflow_agent.start_conversation(
        {
            "llms_context": llms_context,
        }
    )
    conversation.append_user_message(scenario)
    conversation.execute()
    message = conversation.get_last_message()
    if message:
        generated_code = str(message.content).replace("```python", "").replace("\n```", "")
        Path(f"scenario_{scenario_number}_code.py").write_text(generated_code)


def run_agent_with_langgraph(scenario: str, scenario_number: int) -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph import AgentSpecLoader as LangGraphAgentSpecLoader

    loader = LangGraphAgentSpecLoader()
    langgraph_agent = loader.load_component(agent)
    result = langgraph_agent.invoke(
        {
            "llms_context": llms_context,
            "messages": [
                {
                    "role": "user",
                    "content": scenario,
                }
            ],
            "remaining_steps": 1000,
        }
    )
    message: AIMessage = result["messages"][-1]
    if message:
        generated_code = str(message.content).replace("```python", "").replace("\n```", "")
        Path(f"scenario_{scenario_number}_code.py").write_text(generated_code)


if __name__ == "__main__":
    for scenario_number, scenario in enumerate(queries):
        # Run with WayFlow as the runtime
        # run_agent_with_wayflow(scenario, scenario_number)

        # Run with LangGraph as the runtime
        run_agent_with_langgraph(scenario, scenario_number)
