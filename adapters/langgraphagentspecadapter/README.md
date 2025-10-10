# LangGraph Adapter to Open Agent Specification (Agent Spec)

This project demonstrates how an agent defined in LangGraph can be converted to AgentSpec and vice-versa.

## Installation
(1) Run `./install-dev.sh` in order to install the package.

## Usage examples

In this section we show some simple examples of how to use the adapter to transform
Agent Spec configurations into LangGraph components and the other way around.

### LangGraph to Agent Spec

Here's an example of how to use the adapter to transform an LangGraph Assistant to the
corresponding Agent Spec agent translation.

```python
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from langgraph_agentspec_adapter import AgentSpecExporter

def mock_tool() -> str:
    """Mocked tool"""
    return "Useful tool result"

model = ChatOllama(
    model="agi_model",
    base_url=f"http://url_to_my_agi_model/v1",
)
agent = create_react_agent(
    name="langgraph_assistant",
    model=model,
    prompt="Use tools to solve tasks.",
    tools=[mock_tool],
)

exporter = AgentSpecExporter()
agentspec_yaml = exporter.to_yaml(agent)
```

### Agent Spec to LangGraph

Here's an example of how to use the adapter to transform an Agent defined in Agent Spec
to the corresponding LangGraph assistant.

```python
from pyagentspec import Agent
from pyagentspec.llms import OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool
from pyagentspec.serialization import AgentSpecSerializer

from langgraph_agentspec_adapter import AgentSpecLoader

def mock_tool() -> str:
    """Mocked tool"""
    return "Useful tool result"

agent = Agent(
    name="langgraph_assistant",
    description="You are a helpful assistant",
    llm_config=OllamaConfig(
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

langgraph_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(agentspec_yaml)
```

You can now run the loaded assistant as follows.

```python
config = {"configurable": {"thread_id": "1"}}
while True:
    user_input = input("USER  >>> ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = langgraph_assistant.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config,  # type: ignore
    )
    print("AGENT >>>", response['messages'][-1].content.strip())
```

## Additional information

This section documents some useful information related to using the LangGraph adapter for AgentSpec.

### Client Tools

In order to use client tools in LangGraph, we make use of the `interrupt` api (`https://langchain-ai.github.io/langgraph/reference/types/#langgraph.types.interrupt`).
