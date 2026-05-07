# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via LangGraph."""

import pytest
from langchain_core.runnables import RunnableConfig

from pyagentspec.llms import LlmConfig


def _get_bare_llmconfig_openai() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai")


def _get_bare_llmconfig_openai_with_base_url() -> LlmConfig:
    return LlmConfig(
        name="test",
        model_id="gpt-4o",
        api_provider="openai",
        url="https://my-proxy.example.com/v1",
        api_key="sk-test-key",
    )


def _get_bare_llmconfig_openai_with_raw_base_url() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai", url="localhost:8000")


def _get_bare_llmconfig_openai_responses() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai", api_type="responses")


def _get_bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


def test_openai_provider_respects_api_type_responses() -> None:
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    converter = AgentSpecToLangGraphConverter()
    result = converter._llm_convert_to_langgraph(
        _get_bare_llmconfig_openai_responses(), RunnableConfig()
    )
    assert result.use_responses_api is True


def test_openai_provider_defaults_to_chat_completions() -> None:
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    converter = AgentSpecToLangGraphConverter()
    result = converter._llm_convert_to_langgraph(_get_bare_llmconfig_openai(), RunnableConfig())
    assert result.use_responses_api is False


def test_openai_provider_with_base_url_and_api_key() -> None:
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    converter = AgentSpecToLangGraphConverter()
    result = converter._llm_convert_to_langgraph(
        _get_bare_llmconfig_openai_with_base_url(), RunnableConfig()
    )
    assert result.openai_api_base == "https://my-proxy.example.com/v1"
    assert result.openai_api_key.get_secret_value() == "sk-test-key"


def test_openai_provider_with_raw_base_url_adds_scheme() -> None:
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    converter = AgentSpecToLangGraphConverter()
    result = converter._llm_convert_to_langgraph(
        _get_bare_llmconfig_openai_with_raw_base_url(), RunnableConfig()
    )
    assert result.openai_api_base == "http://localhost:8000"


def test_unsupported_provider_raises() -> None:
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    converter = AgentSpecToLangGraphConverter()
    with pytest.raises(NotImplementedError, match="unsupported_provider"):
        converter._llm_convert_to_langgraph(_get_bare_llmconfig_unsupported(), RunnableConfig())
