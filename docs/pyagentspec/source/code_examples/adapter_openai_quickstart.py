# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

# .. start-agentspec_to_runtime
# Create an Agent Spec agent
from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiConfig
from pyagentspec.property import FloatProperty
from pyagentspec.tools import ServerTool

subtraction_tool = ServerTool(
    name="subtraction-tool",
    description="subtract two numbers together",
    inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
    outputs=[FloatProperty(title="difference")],
)

agentspec_agent = Agent(
    name="agentspec_tools_test",
    description="agentspec_tools_test",
    llm_config=OpenAiConfig(name="gpt-5-mini", model_id="gpt-5-mini"),
    system_prompt="Perform subtraction with the given tool.",
    tools=[subtraction_tool],
)

# Export the Agent Spec configuration
from pyagentspec.serialization import AgentSpecSerializer

agentspec_config = AgentSpecSerializer().to_json(agentspec_agent)

# Load and run the Agent Spec configuration with OpenAI Agents
from agents import Runner, TResponseInputItem
from pyagentspec.adapters.openaiagents import AgentSpecLoader

def subtract(a: float, b: float) -> float:
    return a - b

async def main():

    loader = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    assistant = loader.load_json(agentspec_config)
    conversation_history: list[TResponseInputItem] = []

    while True:
        user_input = input("USER >> ")
        if user_input == "exit":
            break

        conversation_history.append({"role": "user", "content": [{"type": "input_text", "text": user_input}]})
        result = await Runner.run(assistant, input=[*conversation_history])
        conversation_history.extend([item.to_input_item() for item in result.new_items])

        print(f"AGENT >> {result.final_output_as(str)}")


# anyio.run(main)
# USER >> Compute 987654321-123456789
# AGENT >> The result of this subtraction is 864197532.
# .. end-agentspec_to_runtime
# .. start-runtime_to_agentspec
# Create an OpenAI Agent
from agents.agent import Agent, function_tool

@function_tool
def subtraction_tool(a: float, b: float) -> float:
    """subtract two numbers together"""
    return a - b

openai_agent = Agent(
    name="openai_agent",
    model="gpt-5-mini",
    instructions="Perform subtraction with the given tool.",
    tools=[subtraction_tool],
)

# Convert to Agent Spec
from pyagentspec.adapters.openaiagents import AgentSpecExporter

agentspec_config = AgentSpecExporter().to_json(openai_agent)
# .. end-runtime_to_agentspec
