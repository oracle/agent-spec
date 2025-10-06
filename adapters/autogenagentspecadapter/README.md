# AutoGen Adapter to Open Agent Specification (Agent Spec)

This project demonstrates how an AutoGen agent can be converted to Agent Spec and vice-versa.

## Installation

Run `./install-dev.sh` in order to install the package.

## Usage examples

In this section we show some simple examples of how to use the adapter to transform
Agent Spec configurations into AutoGen components and the other way around.

### AutoGen to Agent Spec

Here's an example of how to use the adapter to transform an AutoGen Assistant to the
corresponding Agent Spec agent translation.

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.ollama import OllamaChatCompletionClient

from autogen_agentspec_adapter import AgentSpecExporter

async def mock_tool() -> str:
    return "Very helpful tool result"

agent = AssistantAgent(
    name="autogen_assistant",
    model_client=OllamaChatCompletionClient(
        model="agi_model",
        host="url_to_my_agi_model",
        model_info=ModelInfo(
            vision=True,
            function_calling=True,
            json_output=True,
            family=ModelFamily.UNKNOWN,
            structured_output=True,
        ),
    ),
    tools=[mock_tool],
    system_message="Use tools to solve tasks.",
)

exporter = AgentSpecExporter()
agentspec_yaml = exporter.to_yaml(agent)
```

### Agent Spec to AutoGen

Here's an example of how to use the adapter to transform an Agent defined in Agent Spec
to the corresponding AutoGen assistant.

```python
from pyagentspec import Agent
from pyagentspec.llms import OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool
from pyagentspec.serialization import AgentSpecSerializer

from autogen_agentspec_adapter import AgentSpecLoader

async def mock_tool() -> str:
    return "Very helpful tool result"

agent = Agent(
    name="autogen_assistant",
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

autogen_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(agentspec_yaml)
```

You can now run the loaded assistant as follows.

```python
import asyncio
from typing import Any
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

async def assistant_run(agent, input_message: str) -> Any:
    return await agent.on_messages(
        [TextMessage(content=input_message, source="user")],
        cancellation_token=CancellationToken(),
    )

if __name__ == "__main__":
    while True:
        user_input = input("USER  >>> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        response = asyncio.run(assistant_run(autogen_assistant, user_input))
        print("AGENT >>>", response.chat_message.content)
```
