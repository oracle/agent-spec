# Copyright © 2025 Oracle and/or its affiliates.
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
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.property import FloatProperty
from pyagentspec.tools import ServerTool

subtraction_tool = ServerTool(
    name="subtraction-tool",
    description="subtract two numbers together",
    inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
    outputs=[FloatProperty(title="difference")],
)

agentspec_llm_config = OpenAiCompatibleConfig(
    name="llama-3.3-70b-instruct",
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    url="url.to.my.llm",
)

agentspec_agent = Agent(
    name="agentspec_tools_test",
    description="agentspec_tools_test",
    llm_config=agentspec_llm_config,
    system_prompt="Perform subtraction with the given tool.",
    tools=[subtraction_tool],
)

# Export the Agent Spec configuration
from pyagentspec.serialization import AgentSpecSerializer

agentspec_config = AgentSpecSerializer().to_json(agentspec_agent)

# Load and run the Agent Spec configuration with AutoGen
from pyagentspec.adapters.autogen import AgentSpecLoader

def subtract(a: float, b: float) -> float:
    return a - b

async def main() -> None:
    converter = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    component = converter.load_json(agentspec_config)
    while True:
        input_cmd = input("USER >> ")
        if input_cmd == "q":
            break
        result = await component.run(task=input_cmd)
        print(f"AGENT >> {result.messages[-1].content}")
    await component._model_client.close()

# anyio.run(main)
# USER >> Compute 987654321-123456789
# AGENT >> The result of the subtraction is 864197532.
# .. end-agentspec_to_runtime
# .. start-runtime_to_agentspec
# Create an AutoGen Agent
import os
os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def add_tool(a: int, b: int) -> int:
    """Adds a to b and returns the result"""
    return a + b

autogen_tools = {"add_tool": add_tool}

model_client = OpenAIChatCompletionClient(
    model="gpt-4.1",
)

autogen_agent = AssistantAgent(
    name="assistant",
    model_client=model_client,
    tools=list(autogen_tools.values()),
    system_message="Use tools to solve tasks, and reformulate the answers that you get.",
    reflect_on_tool_use=True,
)

# Convert to Agent Spec
from pyagentspec.adapters.autogen import AgentSpecExporter

agentspec_config = AgentSpecExporter().to_json(autogen_agent)
# .. end-runtime_to_agentspec
