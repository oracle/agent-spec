# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.


from langchain_openai.chat_models import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_agentspec_adapter import AgentSpecExporter
from pydantic import SecretStr

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component
from pyagentspec.llms.vllmconfig import VllmConfig

from .conftest import get_weather


def test_convert_llm_config_to_agentspec() -> None:
    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"http://{url}/v1",
    )
    agent = create_react_agent(
        model=model,
        tools=[
            get_weather,
        ],
    )
    agentspec_agent: Component = AgentSpecExporter().to_component(agent)
    assert isinstance(agentspec_agent, AgentSpecAgent)
    config = agentspec_agent.llm_config
    assert isinstance(config, VllmConfig)
    assert config.model_id == model_id
    assert config.url == f"http://{url}/v1"
    assert len(agentspec_agent.tools) == 1
    assert agentspec_agent.tools[0].name == get_weather.__name__
    assert get_weather.__doc__ is not None
    assert agentspec_agent.tools[0].description == get_weather.__doc__.strip()
