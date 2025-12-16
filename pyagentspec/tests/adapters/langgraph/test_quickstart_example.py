# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio
import pytest

from pyagentspec.agent import Agent


@pytest.mark.filterwarnings(
    f"ignore:`config_type` is deprecated and will be removed:DeprecationWarning"
)
def test_quickstart_example_runs(quickstart_agent_json: Agent):
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def subtract(a: float, b: float) -> float:
        return a - b

    async def main():
        loader = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
        assistant = loader.load_json(quickstart_agent_json)

        _ = await assistant.ainvoke(
            input={"messages": [{"role": "user", "content": "Compute 987654321-123456789"}]},
        )

    anyio.run(main)


@pytest.mark.filterwarnings(
    f"ignore:`config_type` is deprecated and will be removed:DeprecationWarning"
)
def test_can_convert_quickstart_example_to_agentspec() -> None:
    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph
    from pydantic import SecretStr
    from typing_extensions import Any, TypedDict

    from pyagentspec.adapters.langgraph import AgentSpecExporter

    class InputSchema(TypedDict):
        city: str

    class OutputSchema(TypedDict):
        response: Any

    class InternalState(TypedDict):
        weather_data: str

    def get_weather(state: InputSchema) -> InternalState:
        """Returns the weather in a specific city.
        Args
        ----
            city: The city to check the weather for

        Returns
        -------
            weather: The weather in that city
        """
        return {"weather_data": f"The weather in {state['city']} is sunny."}

    def llm_node(state: InternalState) -> OutputSchema:
        model = ChatOpenAI(
            base_url="your.url.to.llm/v1",
            model="/storage/models/Llama-3.1-70B-Instruct",
            api_key=SecretStr("t"),
        )
        result = model.invoke(
            f"Reformulate the following sentence to the user: {state['weather_data']}"
        )
        return {"response": result.content}

    graph = StateGraph(InternalState, input_schema=InputSchema, output_schema=OutputSchema)
    graph.add_node("get_weather", get_weather)
    graph.add_node("llm_node", llm_node)
    graph.add_edge(START, "get_weather")
    graph.add_edge("get_weather", "llm_node")
    graph.add_edge("llm_node", END)
    assistant_name = "Weather Flow"
    langgraph_agent = graph.compile(name=assistant_name)

    _ = AgentSpecExporter().to_json(langgraph_agent)
