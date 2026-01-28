# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import yaml

from pyagentspec import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.serialization import AgentSpecSerializer


def test_agentspec_vllm_converts_to_openai_model() -> None:
    from agents.agent import Agent as OAAgent

    from pyagentspec.adapters.openaiagents import AgentSpecLoader

    # AgentSpec with VllmConfig should produce an OA Agent with a Model instance
    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiCompatibleConfig(
            name="local-compat-vllm", model_id="my-vllm-model", url="http://localhost:8000/v1"
        ),
        tools=[],
        system_prompt="You are a helpful assistant.",
    )
    serialized = AgentSpecSerializer().to_yaml(agentspec_agent)

    loader = AgentSpecLoader(tool_registry={})
    oa_agent = loader.load_yaml(serialized)

    assert isinstance(oa_agent, OAAgent)
    # Model should be an Agents SDK Model (not a string)
    from agents.models.interface import Model as OAModel  # type: ignore

    assert isinstance(oa_agent.model, OAModel)

    # Verify base_url propagated to the underlying client
    client = getattr(oa_agent.model, "_client", None)
    base_url = getattr(client, "base_url", None) if client is not None else None
    assert str(base_url).rstrip("/") == "http://localhost:8000/v1"


def test_agentspec_ollama_converts_to_openai_model() -> None:
    from agents.agent import Agent as OAAgent

    from pyagentspec.adapters.openaiagents import AgentSpecLoader

    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiCompatibleConfig(
            name="local-compat-ollama",
            model_id="llama3.1",
            url="http://localhost:11434/v1",
        ),
        tools=[],
        system_prompt="You are a helpful assistant.",
    )
    serialized = AgentSpecSerializer().to_yaml(agentspec_agent)

    loader = AgentSpecLoader(tool_registry={})
    oa_agent = loader.load_yaml(serialized)

    assert isinstance(oa_agent, OAAgent)
    from agents.models.interface import Model as OAModel  # type: ignore

    assert isinstance(oa_agent.model, OAModel)

    client = getattr(oa_agent.model, "_client", None)
    base_url = getattr(client, "base_url", None) if client is not None else None
    assert str(base_url).rstrip("/") == "http://localhost:11434/v1"


def test_export_openai_model_with_base_url_maps_to_openai_compatible() -> None:
    from agents.agent import Agent as OAAgent
    from agents.models.openai_provider import OpenAIProvider
    from openai import AsyncOpenAI

    from pyagentspec.adapters.openaiagents import AgentSpecExporter

    # Build an OA Agent whose model comes from a provider using custom base_url (vLLM)
    provider = OpenAIProvider(
        openai_client=AsyncOpenAI(api_key="", base_url="http://localhost:8000/v1")
    )
    oa_model = provider.get_model("my-vllm-model")

    oa_agent = OAAgent(
        name="assistant",
        instructions="You are a helpful assistant.",
        model=oa_model,
        tools=[],
    )

    exporter = AgentSpecExporter()
    data = yaml.safe_load(exporter.to_yaml(oa_agent))

    assert data["component_type"] == "Agent"
    assert data["llm_config"]["component_type"] == "OpenAiCompatibleConfig"
    assert data["llm_config"]["model_id"] == "my-vllm-model"
    assert data["llm_config"]["url"] == "http://localhost:8000/v1"


def test_export_openai_model_with_ollama_base_url_maps_to_openai_compatible() -> None:
    from agents.agent import Agent as OAAgent
    from agents.models.openai_provider import OpenAIProvider
    from openai import AsyncOpenAI

    from pyagentspec.adapters.openaiagents import AgentSpecExporter

    provider = OpenAIProvider(
        openai_client=AsyncOpenAI(api_key="", base_url="http://localhost:11434/v1")
    )
    oa_model = provider.get_model("llama3.1")

    oa_agent = OAAgent(
        name="assistant",
        instructions="You are a helpful assistant.",
        model=oa_model,
        tools=[],
    )

    exporter = AgentSpecExporter()
    data = yaml.safe_load(exporter.to_yaml(oa_agent))

    assert data["component_type"] == "Agent"
    assert data["llm_config"]["component_type"] == "OpenAiCompatibleConfig"
    assert data["llm_config"]["model_id"] == "llama3.1"
    assert data["llm_config"]["url"] == "http://localhost:11434/v1"
