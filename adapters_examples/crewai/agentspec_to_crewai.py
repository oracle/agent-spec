# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

from pyagentspec.agent import Agent
from pyagentspec.llms import LlmGenerationConfig, VllmConfig
from pyagentspec.property import FloatProperty
from pyagentspec.tools import ClientTool, ServerTool

tools = [
    ClientTool(
        name="sum",
        description="Sum two numbers",
        inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
        outputs=[FloatProperty(title="result")],
    ),
    ClientTool(
        name="subtract",
        description="Subtract two numbers",
        inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
        outputs=[FloatProperty(title="result")],
    ),
    ServerTool(
        name="multiply",
        description="Multiply two numbers",
        inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
        outputs=[FloatProperty(title="result")],
    ),
    ServerTool(
        name="divide",
        description="Divide two numbers",
        inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
        outputs=[FloatProperty(title="result")],
    ),
]

agent = Agent(
    name="calculator_agent",
    description="An agent that provides assistance with tool use.",
    llm_config=VllmConfig(
        name="llama-maverick",
        model_id="Llama-4-Maverick",
        url="url.to.my.llama.model",
        default_generation_parameters=LlmGenerationConfig(temperature=0.1),
    ),
    system_prompt=(
        "You are a helpful calculator agent.\n"
        "Your duty is to compute the result of the given operation using tools, "
        "and to output the result.\n"
        "It's important that you reply with the result only.\n"
    ),
    tools=tools,
)


from pyagentspec.adapters.crewai import AgentSpecLoader

importer = AgentSpecLoader(
    tool_registry={
        "divide": lambda a, b: a / b,
        "multiply": lambda a, b: a * b,
    }
)
calculator_agent = importer.load_component(agent)

from crewai import Crew, Task

task = Task(
    description="{user_input}",
    expected_output="A helpful, concise reply to the user.",
    agent=calculator_agent,
)
crew = Crew(agents=[calculator_agent], tasks=[task])

print("=== Running Crew AI Calculator Agent ===")
while True:
    user_input = input("USER  >>> ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = crew.kickoff(inputs={"user_input": user_input})
    print("AGENT >>>", response)
