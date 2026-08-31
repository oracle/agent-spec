# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langgraphruntime.runtime import (
    AgentSpecFinishedExecutionStatus,
    AgentSpecToolRequestExecutionStatus,
    AgentSpecUserMessageRequestExecutionStatus,
    LanggraphAgentSpecLoader,
    ToolResult,
)

from .conftest import _replace_config_placeholders

CONFIG_DIR = Path(__file__).parent / "configs"


def test_flow_with_llm_node_can_be_run() -> None:
    with open(CONFIG_DIR / "3_flow_with_llm_node_with_template.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())
    runnable_component = LanggraphAgentSpecLoader.load(agentspec_config)
    runnable_component.start({"user_request": "Compute the sequence of Catalan numbers"})
    status = runnable_component.run()
    assert isinstance(status, AgentSpecFinishedExecutionStatus)
    assert "code" in status.outputs
    assert "catalan" in status.outputs["code"].lower()


def test_flow_with_branching_node_and_cycles_can_be_run() -> None:

    def get_parity_tool(number: int) -> str:
        return "odd" if number % 2 else "even"

    def three_times_plus_one_tool(number: int) -> int:
        return 3 * number + 1

    def divide_by_two_tool(number: int) -> int:
        return number // 2

    tool_registry = {
        "get_parity_tool": get_parity_tool,
        "three_times_plus_one_tool": three_times_plus_one_tool,
        "divide_by_two_tool": divide_by_two_tool,
    }

    with open(
        CONFIG_DIR / "4_flow_with_collatz_tool_and_branching_node.yaml"
    ) as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())
    config = RunnableConfig({"configurable": {"thread_id": "1"}, "recursion_limit": 25})
    runnable_component = LanggraphAgentSpecLoader.load(agentspec_config, tool_registry, config)
    runnable_component.start({"number": 5})
    status = runnable_component.run()
    assert isinstance(status, AgentSpecFinishedExecutionStatus)
    assert status.outputs["status"] == "Has converged !!"


def test_agent_can_be_run() -> None:
    with open(CONFIG_DIR / "simple_agent.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())

    runnable_component = LanggraphAgentSpecLoader.load(agentspec_config)
    runnable_component.start()
    runnable_component.append_user_message("Hi, what is 2 * 5?")
    status = runnable_component.run()
    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "10" in status.agent_messages[-1]


def test_agent_with_server_tool_can_be_run() -> None:
    with open(CONFIG_DIR / "weather_agent.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())

    def get_weather(city: str) -> str:
        """Returns the weather in a particular city

        Args
        ----
            city: The city for which to check the weather

        Returns
        -------
            weather: The weather in the city
        """
        return {"agadir": "sunny", "rabat": "cloudy"}.get(city.lower(), "unknown")

    runnable_component = LanggraphAgentSpecLoader.load(
        agentspec_config,
        tool_registry={"get_weather": get_weather},
    )
    runnable_component.start()
    runnable_component.append_user_message("What's the weather like in Agadir?")
    status = runnable_component.run()

    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "sunny" in status.agent_messages[-1].lower()

    runnable_component.append_user_message("What about Rabat?")
    status = runnable_component.run()

    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "cloudy" in status.agent_messages[-1].lower()


def test_agent_with_client_tool_can_be_run() -> None:
    with open(CONFIG_DIR / "weather_agent_client_tool.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())

    runnable_component = LanggraphAgentSpecLoader.load(
        agentspec_config,
    )
    runnable_component.start()
    runnable_component.append_user_message("What's the weather like in Agadir?")
    status = runnable_component.run()

    assert isinstance(status, AgentSpecToolRequestExecutionStatus)
    assert status.tool_requests[0].name == "get_weather"
    assert str(status.tool_requests[0].args.get("city")).lower() == "agadir"

    runnable_component.append_tool_results(
        ToolResult(
            content={"weather": "sunny"},
            tool_request_id=status.tool_requests[0].tool_request_id,
        )
    )
    status = runnable_component.run()

    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "sunny" in status.agent_messages[-1].lower()

    runnable_component.append_user_message("What about Rabat?")
    status = runnable_component.run()

    assert isinstance(status, AgentSpecToolRequestExecutionStatus)
    assert status.tool_requests[0].name == "get_weather"
    assert str(status.tool_requests[0].args.get("city")).lower() == "rabat"

    runnable_component.append_tool_results(
        ToolResult(
            content={"weather": "cloudy"}, tool_request_id=status.tool_requests[0].tool_request_id
        )
    )
    status = runnable_component.run()

    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "cloudy" in status.agent_messages[-1].lower()
