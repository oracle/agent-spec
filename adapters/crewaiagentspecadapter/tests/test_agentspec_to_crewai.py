# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from pathlib import Path

import pytest
from crewai import Crew, Task
from crewai_agentspec_adapter import AgentSpecLoader

from .conftest import IS_JSON_SERVER_RUNNING, JSON_SERVER_PORT

CONFIGS = Path(__file__).parent / "configs"


@pytest.mark.skipif(
    not IS_JSON_SERVER_RUNNING, reason="Skipping test because json server is not running"
)
def test_remote_tool(json_server) -> None:
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    weather_agent = AgentSpecLoader().load_yaml(
        yaml_content.replace(
            "[[remote_tools_server]]", f"http://localhost:{JSON_SERVER_PORT}"
        ).replace("[[LLAMA_API_URL]]", os.environ.get("LLAMA_API_URL"))
    )
    task = Task(
        description="{user_input}",
        expected_output="A helpful, concise reply to the user.",
        agent=weather_agent,
    )
    crew = Crew(agents=[weather_agent], tasks=[task])
    response = crew.kickoff(inputs={"user_input": "What's the weather in Agadir?"})
    assert all(x in str(response) for x in ("Agadir", "sunny")) or all(
        x in str(response) for x in ("agadir", "sunny")
    )
