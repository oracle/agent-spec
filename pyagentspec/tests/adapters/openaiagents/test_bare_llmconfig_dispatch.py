# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via OpenAI Agents."""

import pytest

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


def _get_bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


def test_openai_provider_returns_model_id() -> None:
    from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
        AgentSpecToOpenAIConverter,
    )

    converter = AgentSpecToOpenAIConverter()
    result = converter._llm_convert_to_openai(_get_bare_llmconfig_openai())
    assert result == "gpt-4o"


def test_openai_provider_with_base_url_returns_model() -> None:
    from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
        AgentSpecToOpenAIConverter,
    )
    from pyagentspec.adapters.openaiagents._types import OAChatCompletionsModel

    converter = AgentSpecToOpenAIConverter()
    result = converter._llm_convert_to_openai(_get_bare_llmconfig_openai_with_base_url())
    assert isinstance(result, OAChatCompletionsModel)


def test_unsupported_provider_raises() -> None:
    from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
        AgentSpecToOpenAIConverter,
    )

    converter = AgentSpecToOpenAIConverter()
    with pytest.raises(NotImplementedError, match="unsupported_provider"):
        converter._llm_convert_to_openai(_get_bare_llmconfig_unsupported())
