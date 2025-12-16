# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

exit() # wayflow not installed
# .. start-agentspec_to_runtime
# Create a Agent Spec agent
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

# Load and run the Agent Spec configuration with WayFlow
from wayflowcore.agentspec import AgentSpecLoader

def subtract(a: float, b: float) -> float:
    return a - b

async def main():
    converter = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    assistant = converter.load_json(agentspec_config)
    conversation = assistant.start_conversation()

    while True:
        user_input = input("USER >> ")
        if user_input == "exit":
            break
        conversation.append_user_message(user_input)
        await conversation.execute_async()
        last = conversation.get_last_message()
        print(f"AGENT >> {last.content}")

# anyio.run(main)
# USER >> Compute 987654321-123456789
# AGENT >> The result of the subtraction is 864197532.
# .. end-agentspec_to_runtime
# .. start-runtime_to_agentspec
# Create a WayFlow Agent
from wayflowcore.agent import Agent
from wayflowcore.models import OpenAICompatibleModel
from wayflowcore.tools import tool

@tool("subtraction-tool", description_mode="only_docstring")
def subtraction_tool(a: float, b: float) -> float:
    """subtract two numbers together"""
    return a - b

llm = OpenAICompatibleModel(
    name="llama-3.3-70b-instruct",
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    base_url="url.to.my.llm",
)

wayflow_agent = Agent(
    name="wayflow_agent",
    description="Simple agent with a tool.",
    llm=llm,
    custom_instruction="Perform subtraction with the given tool.",
    tools=[subtraction_tool],
)

# Convert to Agent Spec
from wayflowcore.agentspec import AgentSpecExporter

agentspec_config = AgentSpecExporter().to_json(wayflow_agent)
# .. end-runtime_to_agentspec
