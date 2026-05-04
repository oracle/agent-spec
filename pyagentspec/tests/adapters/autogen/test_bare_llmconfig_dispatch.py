# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for bare LlmConfig adapter dispatch via AutoGen."""

import pytest

from pyagentspec.llms import LlmConfig


def _get_bare_llmconfig_openai() -> LlmConfig:
    return LlmConfig(name="test", model_id="gpt-4o", api_provider="openai")


def _get_bare_llmconfig_openai_with_base_url() -> LlmConfig:
    return LlmConfig(
        name="test",
        model_id="custom-model",
        api_provider="openai",
        url="my-proxy.example.com",
        api_key="sk-test-key",
    )


def _get_bare_llmconfig_unsupported() -> LlmConfig:
    return LlmConfig(name="test", model_id="some-model", api_provider="unsupported_provider")


def test_openai_provider_returns_client() -> None:
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    from pyagentspec.adapters.autogen._autogenconverter import AgentSpecToAutogenConverter

    converter = AgentSpecToAutogenConverter()
    result = converter._llm_convert_to_autogen(
        _get_bare_llmconfig_openai(),
        tool_registry={},
        converted_components={},
    )
    assert isinstance(result, OpenAIChatCompletionClient)


def test_openai_provider_with_base_url_and_api_key() -> None:
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    from pyagentspec.adapters.autogen._autogenconverter import AgentSpecToAutogenConverter
    from pyagentspec.adapters.autogen._types import AutogenModelFamily

    converter = AgentSpecToAutogenConverter()
    result = converter._llm_convert_to_autogen(
        _get_bare_llmconfig_openai_with_base_url(),
        tool_registry={},
        converted_components={},
    )
    assert isinstance(result, OpenAIChatCompletionClient)
    assert result.model_info["family"] == AutogenModelFamily.UNKNOWN
    assert result.model_info["function_calling"] is True


def test_unsupported_provider_raises() -> None:
    from pyagentspec.adapters.autogen._autogenconverter import AgentSpecToAutogenConverter

    converter = AgentSpecToAutogenConverter()
    with pytest.raises(NotImplementedError, match="unsupported_provider"):
        converter._llm_convert_to_autogen(
            _get_bare_llmconfig_unsupported(),
            tool_registry={},
            converted_components={},
        )
