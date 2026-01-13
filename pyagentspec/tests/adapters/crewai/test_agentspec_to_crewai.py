# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path

from ..conftest import _replace_config_placeholders

CONFIGS = Path(__file__).parent / "configs"


def test_remote_tool(json_server: str) -> None:

    from pyagentspec.adapters.crewai import AgentSpecLoader
    from pyagentspec.adapters.crewai._types import crewai

    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    task = crewai.Task(
        description="Use your tool to answer this simple request from the user: {user_input}",
        expected_output="A helpful, concise reply to the user.",
        agent=weather_agent,
    )
    crew = crewai.Crew(agents=[weather_agent], tasks=[task], verbose=False)
    response = crew.kickoff(inputs={"user_input": "What's the weather in Agadir?"})
    assert all(x in str(response) for x in ("Agadir", "sunny")) or all(
        x in str(response) for x in ("agadir", "sunny")
    )
