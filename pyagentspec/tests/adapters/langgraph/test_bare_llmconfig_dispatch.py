# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via LangGraph."""

import pytest

from pyagentspec.llms import LlmConfig


@pytest.fixture
def bare_llmconfig_openai() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai")


@pytest.fixture
def bare_llmconfig_openai_with_base_url() -> LlmConfig:
    return LlmConfig(
        name="test",
        model_id="gpt-4o",
        api_provider="openai",
        url="https://my-proxy.example.com/v1",
        api_key="sk-test-key",
    )


@pytest.fixture
def bare_llmconfig_openai_responses() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai", api_type="responses")


@pytest.fixture
def bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


class TestLangGraphDispatch:
    def test_openai_provider_respects_api_type_responses(
        self, bare_llmconfig_openai_responses: LlmConfig
    ) -> None:
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        converter = AgentSpecToLangGraphConverter()
        result = converter._llm_convert_to_langgraph(bare_llmconfig_openai_responses)
        assert result.use_responses_api is True

    def test_openai_provider_defaults_to_chat_completions(
        self, bare_llmconfig_openai: LlmConfig
    ) -> None:
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        converter = AgentSpecToLangGraphConverter()
        result = converter._llm_convert_to_langgraph(bare_llmconfig_openai)
        assert result.use_responses_api is False

    def test_openai_provider_with_base_url_and_api_key(
        self, bare_llmconfig_openai_with_base_url: LlmConfig
    ) -> None:
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        converter = AgentSpecToLangGraphConverter()
        result = converter._llm_convert_to_langgraph(bare_llmconfig_openai_with_base_url)
        assert result.openai_api_base == "https://my-proxy.example.com/v1"
        assert result.openai_api_key.get_secret_value() == "sk-test-key"

    def test_unsupported_provider_raises(self, bare_llmconfig_unsupported: LlmConfig) -> None:
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        converter = AgentSpecToLangGraphConverter()
        with pytest.raises(NotImplementedError, match="unsupported_provider"):
            converter._llm_convert_to_langgraph(bare_llmconfig_unsupported)
