# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

try:
    import crewai # noqa: F401
except ImportError:
    exit() # Not installed
except RuntimeError as e:
    if "Your system has an unsupported version of sqlite3" in str(e):
        # ChromaDB requires a version of SQLite which is not always supported
        __import__("pysqlite3")
        import sys
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    else:
        raise e # other error

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

# Load and run the Agent Spec configuration with CrewAI
import os
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
from crewai import Crew, Task
from pyagentspec.adapters.crewai import AgentSpecLoader

def subtract(a: float, b: float) -> float:
    return a - b

async def main():
    loader = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    assistant = loader.load_json(agentspec_config)

    while True:
        task = Task(
            description="{user_input}",
            expected_output="A helpful, concise reply to the user.",
            agent=assistant,
            async_execution=True
        )
        crew = Crew(agents=[assistant], tasks=[task])
        user_input = input("USER >> ")
        if user_input == "exit":
            break
        response = await crew.kickoff_async(inputs={"user_input": user_input})
        print(f"AGENT >> {response}")


# anyio.run(main)
# USER >> Compute 987654321-123456789
# AGENT >> 864197532
# .. end-agentspec_to_runtime
# .. start-runtime_to_agentspec
# Create a CrewAI Agent
from crewai import LLM, Agent
from crewai.tools.base_tool import Tool
from pydantic import BaseModel

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

# Convert to Agent Spec
from pyagentspec.adapters.crewai import AgentSpecExporter

agentspec_config = AgentSpecExporter().to_json(crewai_agent)
# .. end-runtime_to_agentspec
