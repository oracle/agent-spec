# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via CrewAI."""

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


def test_openai_provider_returns_llm() -> None:
    from crewai import LLM

    from pyagentspec.adapters.crewai._crewaiconverter import CrewAiConverter

    converter = CrewAiConverter()
    result = converter._llm_convert_to_crewai(_get_bare_llmconfig_openai(), tool_registry={})
    assert isinstance(result, LLM)
    assert result.model == "openai/gpt-4o"


def test_openai_provider_with_base_url_and_api_key() -> None:
    from crewai import LLM

    from pyagentspec.adapters.crewai._crewaiconverter import CrewAiConverter

    converter = CrewAiConverter()
    result = converter._llm_convert_to_crewai(
        _get_bare_llmconfig_openai_with_base_url(), tool_registry={}
    )
    assert isinstance(result, LLM)
    assert result.model == "openai/gpt-4o"
    assert result.api_key == "sk-test-key"


def test_unsupported_provider_raises() -> None:
    from pyagentspec.adapters.crewai._crewaiconverter import CrewAiConverter

    converter = CrewAiConverter()
    with pytest.raises(NotImplementedError, match="unsupported_provider"):
        converter._llm_convert_to_crewai(_get_bare_llmconfig_unsupported(), tool_registry={})
