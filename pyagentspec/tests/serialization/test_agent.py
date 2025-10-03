# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import BooleanProperty, StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


def test_agent_can_be_serialized() -> None:
    vllmconfig = VllmConfig(id="agi1", name="agi1", model_id="agi_model1", url="http://some.where")

    city_input = StringProperty(
        title="city_name",
        default="zurich",
    )
    weather_output = StringProperty(
        title="forecast",
    )
    subscription_success_output = BooleanProperty(
        title="subscription_success",
    )

    weather_tool = ClientTool(
        id="weather_tool",
        name="get_weather",
        description="Gets the weather in specified city",
        inputs=[city_input],
        outputs=[weather_output],
    )

    history_tool = ServerTool(
        id="history_tool",
        name="get_city_history_info",
        description="Gets information about the city history",
        inputs=[city_input],
        outputs=[weather_output],
    )

    newsletter_subscribe_tool = RemoteTool(
        id="city_newsletter_subscribe_tool",
        name="subscribe_to_city_newsletter",
        description="Subscribe to the newsletter of a city",
        url="https://my.url/tool",
        http_method="POST",
        api_spec_uri="https://my.api.spec.url/tool",
        data={"city_name": "{{city_name}}"},
        query_params={"my_query_param": "abc"},
        headers={"my_header": "123"},
        # inputs=[city_input],  #  This is going to be inferred by the tool
        outputs=[subscription_success_output],
    )

    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=[weather_tool, history_tool, newsletter_subscribe_tool],
    )
    serializer = AgentSpecSerializer()
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)
