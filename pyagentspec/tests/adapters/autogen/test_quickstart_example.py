# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio

from pyagentspec.agent import Agent


def test_quickstart_example_runs(quickstart_agent_json: Agent):

    from pyagentspec.adapters.autogen import AgentSpecLoader

    def subtract(a: float, b: float) -> float:
        return a - b

    async def main():
        converter = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
        component = converter.load_json(quickstart_agent_json)
        _ = await component.run(task="Compute 987654321-123456789")

    anyio.run(main)


def test_can_convert_quickstart_example_to_agentspec() -> None:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    from pyagentspec.adapters.autogen import AgentSpecExporter

    async def add_tool(a: int, b: int) -> int:
        """Adds a to b and returns the result"""
        return a + b

    autogen_tools = {"add_tool": add_tool}
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")
    autogen_agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=list(autogen_tools.values()),
        system_message="Use tools to solve tasks, and reformulate the answers that you get.",
        reflect_on_tool_use=True,
    )

    _ = AgentSpecExporter().to_json(autogen_agent)
