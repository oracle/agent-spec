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

# Load and run the Agent Spec configuration with Microsoft Agent Framework
from pyagentspec.adapters.agent_framework import AgentSpecLoader

def subtract(a: float, b: float) -> float:
    return a - b

async def main():
    from agent_framework import TextContent
    loader = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    assistant = loader.load_json(agentspec_config)

    while True:
        user_input = input("USER >> ")
        if user_input == "exit":
            break
        result = await assistant.run(user_input)
        agent_message = result.messages[-1].contents[-1]
        if not isinstance(agent_message, TextContent):
            raise ValueError(f"Unexpected agent_message type {type(agent_message)}")
        print(f"AGENT >> {agent_message.text}")


# anyio.run(main)
# USER >> Compute 987654321-123456789
# AGENT >> The result of this subtraction is 864197532.
# .. end-agentspec_to_runtime
# .. start-runtime_to_agentspec
# Create an Agent Framework Agent
from agent_framework import ChatAgent, tool
from agent_framework.openai import OpenAIChatClient

@tool()
def get_weather(city: str) -> str:
    """Returns the weather in a specific city.
    Args
    ----
        city: The city to check the weather for

    Returns
    -------
        weather: The weather in that city
    """
    return f"The weather in {city} is sunny."

agent_framework_agent = ChatAgent(
    chat_client=OpenAIChatClient(
        api_key="ollama",
        base_url="url.to.agi.model",
        model_id="agi_ollama_model",
    ),
    name="Weather Agent",
    instructions="You are a weather agent. Use the provided tool to get data related to the weather based on the city mentioned in the user query.",
    tools=get_weather,
)

# Convert to Agent Spec
from pyagentspec.adapters.agent_framework import AgentSpecExporter

agentspec_config = AgentSpecExporter().to_json(agent_framework_agent)
# .. end-runtime_to_agentspec
