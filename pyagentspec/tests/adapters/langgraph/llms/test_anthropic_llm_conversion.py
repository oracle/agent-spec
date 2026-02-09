# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest


def test_agentspec_to_langgraph_converts_anthropic_llm_config_to_chat_anthropic() -> None:
    pytest.importorskip("langchain_anthropic")

    from langchain_anthropic import ChatAnthropic
    from langchain_core.runnables import RunnableConfig

    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
    from pyagentspec.llms import AnthropicLlmConfig, LlmGenerationConfig

    model_id: str = "test-anthropic-model"
    base_url: str = "https://api.test-anthropic.com"
    max_tokens: int = 123
    temperature: float = 0.7
    top_p: float = 0.9

    agentspec_config = AnthropicLlmConfig(
        name="test-name",
        model_id=model_id,
        base_url=base_url,
        default_generation_parameters=LlmGenerationConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        ),
    )

    model = AgentSpecToLangGraphConverter()._llm_convert_to_langgraph(
        agentspec_config, RunnableConfig({})
    )

    assert isinstance(model, ChatAnthropic)
    assert model.model == model_id
    assert model.anthropic_api_url == base_url
    assert model.max_tokens == max_tokens
    assert model.temperature == temperature
    assert model.top_p == top_p


def test_langgraph_to_agentspec_converts_chat_anthropic_to_anthropic_llm_config() -> None:
    pytest.importorskip("langchain_anthropic")

    from langchain_anthropic import ChatAnthropic

    from pyagentspec.adapters.langgraph._agentspecconverter import LangGraphToAgentSpecConverter
    from pyagentspec.llms import AnthropicLlmConfig

    model_id: str = "test-anthropic-model"
    base_url: str = "https://api.test-anthropic.com"

    model = ChatAnthropic(
        model=model_id,
        base_url=base_url,
    )

    agentspec_config = LangGraphToAgentSpecConverter().convert(model)
    assert isinstance(agentspec_config, AnthropicLlmConfig)
    assert agentspec_config.name == model_id
    assert agentspec_config.model_id == model_id
    assert agentspec_config.base_url == base_url
