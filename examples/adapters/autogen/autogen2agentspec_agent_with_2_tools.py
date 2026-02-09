# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


# mypy: ignore-errors

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.ollama import OllamaChatCompletionClient
from wayflowcore.agentspec import AgentSpecLoader
from wayflowcore.executors.executionstatus import FinishedStatus
from wayflowcore.property import StringProperty
from wayflowcore.tools import ServerTool as WayflowServerTool

from pyagentspec.adapters.autogen import AgentSpecExporter


async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is 30 degrees and Sunny."


async def get_capital(country: str) -> str:
    """Get the capital for a given country."""
    return f"The capital of {country} is Rabat."


def agentspec_get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is 30 degrees and Sunny."


def agentspec_get_capital(country: str) -> str:
    """Get the capital for a given country."""
    return f"The capital of {country} is Rabat."


def test_autogen_agent_can_be_converted_to_agentspec() -> None:

    model_client = OllamaChatCompletionClient(
        model="llama3.2:latest",
        host="localhost:11434",
    )

    agent = AssistantAgent(
        name="autogen_assistant",
        model_client=model_client,
        tools=[get_weather, get_capital],
        system_message="Use tools to solve tasks.",
    )

    # -- AutoGen test --

    async def assistant_run() -> None:

        # -- First test --
        response = await agent.on_messages(
            [TextMessage(content="What is the capital of Morocco?", source="user")],
            cancellation_token=CancellationToken(),
        )

        print(response)

        # -- Second test --
        response = await agent.on_messages(
            [TextMessage(content="What is the weather in casablanca?", source="user")],
            cancellation_token=CancellationToken(),
        )

        print(response)

    asyncio.run(assistant_run())

    exporter = AgentSpecExporter()

    agentspec_yaml = exporter.to_yaml(agent)

    # -- WayFlow test --
    wf_get_weather = WayflowServerTool(
        "get_weather",
        "Get the weather for a given city.",
        agentspec_get_weather,
        input_descriptors=[StringProperty("city")],
        output_descriptors=[StringProperty("weather_result")],
    )
    wf_get_capital = WayflowServerTool(
        "get_capital",
        "Get the capital for a given country.",
        agentspec_get_capital,
        input_descriptors=[StringProperty("country")],
        output_descriptors=[StringProperty("capital_result")],
    )
    loader = AgentSpecLoader(
        tool_registry={"get_weather": wf_get_weather, "get_capital": wf_get_capital}
    )

    assistant = loader.load_yaml(agentspec_yaml)

    def run_agent_in_command_line(assistant) -> None:
        conversation = assistant.start_conversation(
            inputs={agent.name + "_input": "What is the capital of Morocco?"}
        )

        while True:
            status = assistant.execute(conversation)
            finished = isinstance(status, FinishedStatus)
            assistant_reply = conversation.get_last_message()
            print("Assistant>>> ", assistant_reply.content, "\n")

            if finished:
                print("(done.)")
                break
            else:
                user_input = input("User>>> ")
                print("\n")
                conversation.append_user_message(user_input)

    run_agent_in_command_line(assistant)


test_autogen_agent_can_be_converted_to_agentspec()
