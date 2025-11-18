# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pydantic
import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import BooleanProperty, FloatProperty, IntegerProperty, StringProperty
from pyagentspec.specialized_agent import AgentSpecializationParameters, SpecializedAgent
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool


@pytest.fixture()
def model_config():
    yield VllmConfig(id="agi1", name="agi1", model_id="agi_model1", url="http://some.where")


@pytest.fixture()
def tools():
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
        id="cat_newsletter_subscribe_tool",
        name="subscribe_to_cat_newsletter",
        description="Subscribe to the newsletter of a cat shelter",
        url="https://my.url/tool",
        http_method="POST",
        api_spec_uri="https://my.api.spec.url/tool",
        data={"cat_name": "{{cat_name}}"},
        query_params={"my_query_param": "abc"},
        headers={"my_header": "123"},
        outputs=[subscription_success_output],
    )
    yield [weather_tool, history_tool, newsletter_subscribe_tool]


def test_specialized_agent_inferred_inputs(model_config, tools) -> None:
    agent = Agent(
        name="Funny agent",
        llm_config=model_config,
        system_prompt="No matter what the user asks, don't reply but make a joke about {{topic}} instead",
        tools=tools[:2],
    )

    agent_specialization_parameters = AgentSpecializationParameters(
        name="cat specialization",
        additional_instructions="Only ever tell jokes about cats. You are all about cats named {{name}}",
        additional_tools=tools[2:],
    )

    specialized_agent = SpecializedAgent(
        name="Funny cat agent",
        agent=agent,
        agent_specialization_parameters=agent_specialization_parameters,
    )

    assert isinstance(specialized_agent.inputs, list)
    assert len(specialized_agent.inputs) == 2
    assert specialized_agent.inputs[0].title == "topic"
    assert specialized_agent.inputs[1].title == "name"
    assert specialized_agent.outputs == []


def test_specialized_agent_inferred_outputs(model_config, tools) -> None:
    agent = Agent(
        name="Funny agent",
        llm_config=model_config,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        outputs=[StringProperty(title="funny_joke")],
        tools=tools[:2],
    )

    agent_specialization_parameters = AgentSpecializationParameters(
        name="cat specialization",
        additional_instructions="Only ever tell jokes about cats. You are all about cats.",
        additional_tools=tools[2:],
    )

    specialized_agent = SpecializedAgent(
        name="Funny cat agent",
        agent=agent,
        agent_specialization_parameters=agent_specialization_parameters,
    )

    assert isinstance(specialized_agent.outputs, list)
    assert len(specialized_agent.outputs) == 1
    assert specialized_agent.outputs[0].title == "funny_joke"
    assert specialized_agent.inputs == []

    with pytest.raises(pydantic.ValidationError):
        # We don't allow specializing the outputs of the agent
        agent_specialization_parameters = AgentSpecializationParameters(
            name="cat specialization",
            additional_instructions="Only ever tell jokes about cats. You are all about cats.",
            additional_tools=tools[2:],
            outputs=[StringProperty(title="funny_cat_joke")],
        )


def test_specialized_agent_with_duplicated_inputs(model_config, tools):
    agent = Agent(
        name="Funny agent aware of user's name",
        llm_config=model_config,
        system_prompt="No matter what the user {{user_name}} asks, don't reply but make a joke instead",
        tools=tools[:2],
    )

    agent_specialization_parameters = AgentSpecializationParameters(
        name="cat specialization",
        additional_instructions="Only ever tell jokes about cats. You are all about cats named {{user_name}}",
        additional_tools=tools[2:],
        human_in_the_loop=False,
    )

    specialized_agent = SpecializedAgent(
        name="Funny cat agent",
        agent=agent,
        agent_specialization_parameters=agent_specialization_parameters,
    )
    # Deduplication is working...
    assert specialized_agent.inputs == [StringProperty(title="user_name")]

    agent = Agent(
        name="Funny agent aware of user's name",
        llm_config=model_config,
        system_prompt="No matter what the user {{user_name}} (age: {{user_age}}) asks, don't reply but make a joke instead",
        inputs=[StringProperty(title="user_name"), FloatProperty(title="user_age")],
        tools=tools[:2],
    )
    agent_specialization_parameters = AgentSpecializationParameters(
        name="cat specialization",
        additional_instructions="Only ever tell jokes about cats. You are all about cats named {{user_name}} (age: {{user_age}})",
        additional_tools=tools[2:],
        inputs=[StringProperty(title="user_name"), IntegerProperty(title="user_age")],
        human_in_the_loop=False,
    )

    with pytest.raises(pydantic.ValidationError):
        # ...but only if the properties have the same types
        specialized_agent = SpecializedAgent(
            name="Funny cat agent",
            agent=agent,
            agent_specialization_parameters=agent_specialization_parameters,
        )
