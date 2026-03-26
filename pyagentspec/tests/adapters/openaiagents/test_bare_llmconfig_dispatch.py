# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via OpenAI Agents."""

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
def bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


class TestOpenAiAgentsDispatch:
    def test_openai_provider_returns_model_id(self, bare_llmconfig_openai: LlmConfig) -> None:
        from pyagentspec.adapters.openaiagents._openaiagentsconverter import OpenAiAgentsConverter

        converter = OpenAiAgentsConverter()
        result = converter._llm_convert_to_openai(bare_llmconfig_openai)
        assert result == "gpt-4o"

    def test_openai_provider_with_base_url_returns_model(
        self, bare_llmconfig_openai_with_base_url: LlmConfig
    ) -> None:
        from agents.models.chatcmpl_model import ChatCmplModel

        from pyagentspec.adapters.openaiagents._openaiagentsconverter import OpenAiAgentsConverter

        converter = OpenAiAgentsConverter()
        result = converter._llm_convert_to_openai(bare_llmconfig_openai_with_base_url)
        # When base_url is set, should return a ChatCmplModel (OAChatCompletionsModel) not a string
        assert isinstance(result, ChatCmplModel)

    def test_unsupported_provider_raises(self, bare_llmconfig_unsupported: LlmConfig) -> None:
        from pyagentspec.adapters.openaiagents._openaiagentsconverter import OpenAiAgentsConverter

        converter = OpenAiAgentsConverter()
        with pytest.raises(NotImplementedError, match="unsupported_provider"):
            converter._llm_convert_to_openai(bare_llmconfig_unsupported)
