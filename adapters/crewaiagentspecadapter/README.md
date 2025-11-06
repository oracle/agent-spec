# CrewAI Adapter to Open Agent Specification (Agent Spec)

This project demonstrates how an agent defined in CrewAI can be converted to Agent Spec and vice-versa.


## Installation
Run `./install-dev.sh` in order to install the package.

## Usage examples

In this section we show some simple examples of how to use the adapter to transform
Agent Spec configurations into CrewAI components and the other way around.

### CrewAI to Agent Spec

Here's an example of how to use the adapter to transform a CrewAI Assistant to the
corresponding Agent Spec agent translation.

```python
from crewai import LLM as CrewAILlm
from crewai import Agent as CrewAIAgent
from crewai.tools.base_tool import Tool as CrewAIServerTool
from pydantic import BaseModel

from crewai_agentspec_adapter import AgentSpecExporter

def mock_tool() -> str:
    return "Very helpful tool result"

class MockToolSchema(BaseModel):
    pass

crewai_mock_tool = CrewAIServerTool(
    name="mock_tool",
    description="Mocked tool",
    args_schema=MockToolSchema,
    func=mock_tool,
)

agent = CrewAIAgent(
    role="crew_ai_assistant",
    goal="Use tools to solve tasks.",
    backstory="You are a helpful assistant",
    llm=CrewAILlm(
        model="ollama/agi_model",
        base_url="url_to_my_agi_model",
    ),
    tools=[crewai_mock_tool],
)

exporter = AgentSpecExporter()
agentspec_yaml = exporter.to_yaml(agent)
```

### Agent Spec to CrewAI

Here's an example of how to use the adapter to transform an Agent defined in Agent Spec
to the corresponding CrewAI assistant.

```python
from pyagentspec import Agent
from pyagentspec.llms import OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool
from pyagentspec.serialization import AgentSpecSerializer

from crewai_agentspec_adapter import AgentSpecLoader

def mock_tool() -> str:
    return "Very helpful tool result"

agent = Agent(
    name="crew_ai_assistant",
    description="You are a helpful assistant",
    llm_config=OllamaConfig(
        # Replace this with your LLM configuration
        name="agi_model",
        model_id="agi_model",
        url="url_to_my_agi_model",
    ),
    tools=[
        ServerTool(name="mock_tool", inputs=[], outputs=[StringProperty(title="mock_tool")])
    ],
    system_prompt="Use tools to solve tasks.",
)
agentspec_yaml = AgentSpecSerializer().to_yaml(agent)

crewai_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(agentspec_yaml)
```

You can now run the loaded assistant as follows.

```python
from crewai import Crew, Task

task = Task(
    description="{user_input}",
    expected_output="A helpful, concise reply to the user.",
    agent=crewai_assistant,
)
crew = Crew(agents=[crewai_assistant], tasks=[task])

while True:
    user_input = input("USER  >>> ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = crew.kickoff(inputs={"user_input": user_input})
    print("AGENT >>>", response)
```

## Additional information

This section documents some useful information related to using the CrewAI adapter for AgentSpec.

### Execution

Before running the examples, you can prevent CrewAI from trying to contact its telemetry service by setting

```bash
export CREWAI_DISABLE_TELEMETRY=true
```
