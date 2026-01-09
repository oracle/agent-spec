# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

import pytest
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from pyagentspec.adapters.langgraph._langgraphconverter import (
    AgentSpecToLangGraphConverter,
    _prepare_openai_compatible_url,
)
from pyagentspec.llms.ollamaconfig import OllamaConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType, OpenAiCompatibleConfig
from pyagentspec.llms.vllmconfig import VllmConfig


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("localhost:8000", "http://localhost:8000/v1"),
        ("127.0.0.1:5000", "http://127.0.0.1:5000/v1"),
        ("https://api.example.com", "https://api.example.com/v1"),
        ("http://my-host/api/v2", "http://my-host/v1"),
        (" my-host:9999  ", "http://my-host:9999/v1"),
    ],
)
def test_prepare_openai_compatible_url_formats_various_inputs(raw: str, expected: str) -> None:
    assert _prepare_openai_compatible_url(raw) == expected


def test_vllm_conversion_maps_url_and_generation_config(default_generation_parameters):
    agentspec_llm = VllmConfig(
        name="llm",
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
        url="localhost:8000",  # missing scheme on purpose
        default_generation_parameters=default_generation_parameters,
    )

    model = AgentSpecToLangGraphConverter().convert(agentspec_llm, {})

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == agentspec_llm.model_id
    base = model.openai_api_base
    assert isinstance(base, str) and base.endswith("/v1") and base.startswith("http://")
    assert model.use_responses_api is False
    assert model.temperature == default_generation_parameters.temperature


@pytest.mark.parametrize(
    "api_type, expected_flag",
    [
        (OpenAIAPIType.RESPONSES, True),
        (OpenAIAPIType.CHAT_COMPLETIONS, False),
    ],
)
def test_openaicompatible_conversion_sets_responses_flag(
    api_type, expected_flag, monkeypatch, default_generation_parameters
):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "DUMMY_KEY"))
    agentspec_llm = OpenAiCompatibleConfig(
        name="oaic",
        model_id="gpt-4o-mini",
        url="https://api.compatible",
        api_type=api_type,
        default_generation_parameters=default_generation_parameters,
    )

    model = AgentSpecToLangGraphConverter().convert(agentspec_llm, {})

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"
    assert model.openai_api_base.endswith("/v1")
    assert model.use_responses_api is expected_flag
    assert model.max_tokens == default_generation_parameters.max_tokens
    assert model.temperature == default_generation_parameters.temperature


def test_ollama_conversion_maps_generation_config_names(default_generation_parameters):
    agentspec_llm = OllamaConfig(
        name="oll",
        model_id="llama3.1",
        url="http://ollama.local:11434",
        default_generation_parameters=default_generation_parameters,
    )

    model = AgentSpecToLangGraphConverter().convert(agentspec_llm, {})

    assert isinstance(model, ChatOllama)
    assert model.base_url == "http://ollama.local:11434"
    assert model.model == "llama3.1"
    assert model.temperature == default_generation_parameters.temperature
    assert model.num_predict == default_generation_parameters.max_tokens
    assert model.top_p == default_generation_parameters.top_p


def test_invoke_vllm_model(default_generation_parameters, monkeypatch):
    agentspec_llm = OpenAiCompatibleConfig(
        name="llama33",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.getenv("LLAMA70BV33_API_URL"),
        default_generation_parameters=default_generation_parameters,
    )
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "not needed"))
    model = AgentSpecToLangGraphConverter().convert(agentspec_llm, {})
    assert isinstance(model, ChatOpenAI)
    assert model.max_tokens == default_generation_parameters.max_tokens
    resp = model.invoke("What is 1+1?")
    assert resp is not None
