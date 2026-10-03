#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path

from autogen_agentchat.messages import TextMessage
from autogen_core.tools import FunctionTool as AutogenFunctionTool
from autogenruntime.runtime import (
    AgentSpecUserMessageRequestExecutionStatus,
    AutogenAgentSpecLoader,
)

from .conftest import _replace_config_placeholders

CONFIG_DIR = Path(__file__).parent / "configs"


async def test_agent_can_be_run() -> None:
    with open(CONFIG_DIR / "simple_agent.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())

    runnable_component = AutogenAgentSpecLoader.load(agentspec_config)
    runnable_component.start([TextMessage(source="User", content="Hi, what is 2 * 5?")])
    status = runnable_component.run()
    assert isinstance(status, AgentSpecUserMessageRequestExecutionStatus)
    assert "10" in status.agent_messages[-1]


async def test_agent_with_server_tool_can_be_run() -> None:
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

    runnable_component = AutogenAgentSpecLoader.load(
        agentspec_config,
        tool_registry={"get_weather": AutogenFunctionTool(description="", func=get_weather)},
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
