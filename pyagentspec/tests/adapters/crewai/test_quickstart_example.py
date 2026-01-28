# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio

from pyagentspec.agent import Agent


def test_quickstart_example_runs(quickstart_agent_json: Agent):

    from crewai import Crew, Task

    from pyagentspec.adapters.crewai import AgentSpecLoader

    def subtract(a: float, b: float) -> float:
        return a - b

    async def main():
        loader = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
        assistant = loader.load_json(quickstart_agent_json)

        task = Task(
            description="{user_input}",
            expected_output="A helpful, concise reply to the user.",
            agent=assistant,
            async_execution=True,
        )
        crew = Crew(agents=[assistant], tasks=[task])
        _ = await crew.kickoff_async(inputs={"user_input": "Compute 987654321-123456789"})

    anyio.run(main)


def test_can_convert_quickstart_example_to_agentspec() -> None:
    from crewai import LLM, Agent
    from crewai.tools.base_tool import Tool
    from pydantic import BaseModel

    from pyagentspec.adapters.crewai import AgentSpecExporter

    class InputSchema(BaseModel):
        a: float
        b: float

    def subtract(a: float, b: float) -> float:
        """Subtract two numbers"""
        return a - b

    llm = LLM(
        model="hosted_vllm/Llama-4-Maverick",
        api_base="http://url.to.my.llama.model/v1",
        max_tokens=512,
    )

    crewai_agent = Agent(
        role="Calculator agent",
        goal="Computes the mathematical operation prompted by the user",
        backstory="You are a calculator with 20 years of experience",
        llm=llm,
        tools=[
            Tool(
                name="subtract",
                description="Subtract two numbers",
                args_schema=InputSchema,
                func=subtract,
            ),
        ],
    )
    _ = AgentSpecExporter().to_json(crewai_agent)
