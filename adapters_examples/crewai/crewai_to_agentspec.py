# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

from crewai import LLM, Agent
from crewai.tools.base_tool import Tool
from pydantic import BaseModel


class InputSchema(BaseModel):
    a: float
    b: float


def sum_(a: float, b: float) -> float:
    """Sum two numbers"""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract two numbers"""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    return a / b


llm = LLM(
    model="hosted_vllm/Llama-4-Maverick",
    api_base="http://url.to.my.llama.model/v1",
    max_tokens=512,
)

calculator_agent = Agent(
    role="Calculator agent",
    goal="Computes the mathematical operation prompted by the user",
    backstory="You are a calculator with 20 years of experience",
    llm=llm,
    tools=[
        Tool(
            name="sum",
            description="Sum two numbers",
            args_schema=InputSchema,
            func=sum_,
        ),
        Tool(
            name="subtract",
            description="Subtract two numbers",
            args_schema=InputSchema,
            func=subtract,
        ),
        Tool(
            name="divide",
            description="Divide two numbers",
            args_schema=InputSchema,
            func=divide,
        ),
        Tool(
            name="multiply",
            description="Multiply two numbers",
            args_schema=InputSchema,
            func=multiply,
        ),
    ],
)


if __name__ == "__main__":

    from crewai import Crew, Task

    task = Task(
        description="{history}",
        expected_output="A helpful, concise reply to the user.",
        agent=calculator_agent,
    )
    crew = Crew(agents=[calculator_agent], tasks=[task])

    history = []
    while True:
        user_input = input("USER  >>> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        history.append(f"User: {user_input}")
        response = crew.kickoff(inputs={"history": history})
        history.append(f"Agent: {response}")
        print("AGENT >>>", response)

    from pyagentspec.adapters.crewai import AgentSpecExporter

    exporter = AgentSpecExporter()
    agentspec_yaml = exporter.to_yaml(calculator_agent)
    print(agentspec_yaml)
