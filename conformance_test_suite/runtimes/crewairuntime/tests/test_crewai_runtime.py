#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import os
from pathlib import Path

from crewai.tools.base_tool import Tool
from crewairuntime.runtime import (
    AgentSpecUserMessageRequestExecutionStatus,
    CrewAIAgentSpecLoader,
)
from pydantic import BaseModel

from pyagentspec import Agent, AgentSpecSerializer
from pyagentspec.llms import VllmConfig

from .conftest import _replace_config_placeholders
from .testhelpers import retry_test

CONFIG_DIR = Path(__file__).parent / "configs"


def test_agent_can_be_run() -> None:
    with open(CONFIG_DIR / "simple_agent.yaml") as agentspec_config_file:
        agentspec_config = _replace_config_placeholders(agentspec_config_file.read())

    runnable_component = CrewAIAgentSpecLoader.load(agentspec_config)
    runnable_component.start({"messages": [{"role": "user", "content": "Hi, what is 2 * 5?"}]})
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

    class InputSchema(BaseModel):
        city: str

    runnable_component = CrewAIAgentSpecLoader.load(
        agentspec_config,
        tool_registry={
            "get_weather": Tool(
                name="get_weather",
                description="Gets the weather",
                args_schema=InputSchema,
                func=get_weather,
            )
        },
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


@retry_test(max_attempts=3)
def test_agent_correctly_uses_info_from_long_conversation():
    """
    Failure rate:          0 out of 100
    Observed on:           2025-10-28
    Average success time:  11.39 seconds per successful attempt
    Average failure time:  No time measurement
    Max attempt:           2
    Justification:         (0.01 ** 2) ~= 9.6 / 100'000
    """

    llm_config = VllmConfig(
        name="vllm",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.environ.get("LLAMA70BV33_API_URL"),
    )
    agent = Agent(name="my_agent", llm_config=llm_config, system_prompt="Be helpful")
    agent_as_yaml = AgentSpecSerializer().to_yaml(agent)
    runnable_component = CrewAIAgentSpecLoader().load(agent_as_yaml)
    runnable_component.start()
    runnable_component.append_user_message("My name is Pete")
    runnable_component.run()
    runnable_component.append_user_message("I am an architect")
    runnable_component.run()
    runnable_component.append_user_message("I live in Canada")
    runnable_component.run()
    runnable_component.append_user_message("I have a daughter named Lucie")
    runnable_component.run()
    runnable_component.append_user_message(
        "Please repeat (1) my name (2) my job (3) my country (4) my daughter's name"
    )
    status = runnable_component.run()
    for word in ["pete", "architect", "canada", "lucie"]:
        assert word in status.agent_messages[-1].lower()
