# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import asyncio
import json
from typing import Any

import yaml

from pyagentspec import Agent
from pyagentspec.llms import OpenAiConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool


def test_agentspec_client_tool_converts_and_prompts(monkeypatch) -> None:
    from pyagentspec.adapters.openaiagents import AgentSpecLoader
    from pyagentspec.adapters.openaiagents._types import (
        OAAgent,
        OAFunctionTool,
    )

    # Build an AgentSpec Agent with a ClientTool (interactive bridge)
    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiConfig(name="gpt-4.1", model_id="gpt-4.1"),
        tools=[
            ClientTool(
                name="ask_user",
                description="Ask the user a question.",
                inputs=[StringProperty(title="question")],
                outputs=[StringProperty(title="answer")],
            )
        ],
        system_prompt="You are a helpful assistant.",
    )

    serialized = AgentSpecSerializer().to_yaml(agentspec_agent)

    # Patch input() so the tool's on_invoke_tool returns a deterministic value
    monkeypatch.setattr("builtins.input", lambda prompt: "approved")

    loader = AgentSpecLoader(tool_registry={})
    oa_agent = loader.load_yaml(serialized)
    assert isinstance(oa_agent, OAAgent)
    assert len(oa_agent.tools) == 1
    tool = oa_agent.tools[0]
    assert isinstance(tool, OAFunctionTool)

    # Invoke the tool's async on_invoke_tool with dummy context and input JSON
    async def invoke_tool():
        return await tool.on_invoke_tool(None, json.dumps({"question": "Proceed?"}))  # type: ignore[arg-type]

    result = asyncio.run(invoke_tool())
    assert result == "approved"


def test_agentspec_remote_tool_converts_and_calls_httpx(monkeypatch) -> None:
    from pyagentspec.adapters.openaiagents import AgentSpecLoader
    from pyagentspec.adapters.openaiagents._types import (
        OAAgent,
        OAFunctionTool,
    )

    # Build an AgentSpec Agent with a RemoteTool that renders templates and calls httpx.request
    remote = RemoteTool(
        name="get_weather_remote",
        description="Fetch weather for a city via HTTP.",
        http_method="GET",
        url="https://api.example.com/weather",
        headers={"X-Auth": "{{auth}}"},
        query_params={"city": "{{city}}"},
        data={},
        inputs=[StringProperty(title="city"), StringProperty(title="auth")],
        outputs=[StringProperty(title="result")],
    )
    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiConfig(name="gpt-4.1", model_id="gpt-4.1"),
        tools=[remote],
        system_prompt="You are a helpful assistant.",
    )

    serialized = AgentSpecSerializer().to_yaml(agentspec_agent)

    # Mock httpx.request used inside the adapter
    captured: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self, payload: Any):
            self._payload = payload

        def json(self) -> Any:
            return self._payload

        @property
        def text(self) -> str:
            return json.dumps(self._payload)

    def _fake_request(method: str, url: str, params=None, data=None, headers=None, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params or {}
        captured["data"] = data or {}
        captured["headers"] = headers or {}
        return _FakeResponse({"temp_f": 72, "city": captured["params"].get("city")})

    # Patch the httpx.request imported in the converter module
    monkeypatch.setattr(
        "pyagentspec.adapters._tools_common.httpx.request",
        _fake_request,
        raising=True,
    )

    loader = AgentSpecLoader(tool_registry={})
    oa_agent = loader.load_yaml(serialized)
    assert isinstance(oa_agent, OAAgent)
    assert len(oa_agent.tools) == 1
    tool = oa_agent.tools[0]
    assert isinstance(tool, OAFunctionTool)

    # Invoke tool and assert that httpx.request was called with rendered inputs
    async def invoke_tool():
        args = {"city": "San Francisco", "auth": "token-123"}
        return await tool.on_invoke_tool(None, json.dumps(args))  # type: ignore[arg-type]

    result = asyncio.run(invoke_tool())

    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.example.com/weather"
    assert captured["params"] == {"city": "San Francisco"}
    assert captured["headers"] == {"X-Auth": "token-123"}
    assert isinstance(result, dict)
    assert result["temp_f"] == 72
    assert result["city"] == "San Francisco"


def test_round_trip_agentspec_to_openai_to_agentspec() -> None:
    from pyagentspec.adapters.openaiagents import AgentSpecExporter, AgentSpecLoader
    from pyagentspec.adapters.openaiagents._types import (
        OAAgent,
        OAFunctionTool,
    )

    # Start with AgentSpec with one ServerTool
    def _weather(city: str) -> str:
        return f"Sunny in {city}"

    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiConfig(name="gpt-4.1", model_id="gpt-4.1"),
        tools=[
            ServerTool(
                name="get_weather",
                description="Return weather by city",
                inputs=[StringProperty(title="city")],
                outputs=[StringProperty(title="result")],
            )
        ],
        system_prompt="You are a helpful assistant.",
    )
    orig_yaml = AgentSpecSerializer().to_yaml(agentspec_agent)

    # Convert to OpenAI Agent
    loader = AgentSpecLoader(tool_registry={"get_weather": _weather})
    oa_agent = loader.load_yaml(orig_yaml)
    assert isinstance(oa_agent, OAAgent)
    assert oa_agent.name == "assistant"
    assert oa_agent.instructions == "You are a helpful assistant."
    assert len(oa_agent.tools) == 1
    assert isinstance(oa_agent.tools[0], OAFunctionTool)
    assert oa_agent.tools[0].name == "get_weather"

    # Export back to AgentSpec
    exporter = AgentSpecExporter()
    roundtrip_yaml = exporter.to_yaml(oa_agent)
    data = yaml.safe_load(roundtrip_yaml)

    assert data["component_type"] == "Agent"
    # Compare against the round-tripped OA agent's attributes
    assert data["name"] == oa_agent.name
    assert data["system_prompt"] == oa_agent.instructions
    assert data["llm_config"]["component_type"] == "OpenAiConfig"
    # OAAgent.model is a string like "gpt-4.1" that should map to model_id
    assert data["llm_config"]["model_id"] == oa_agent.model
    assert isinstance(data["tools"], list) and len(data["tools"]) == len(oa_agent.tools)
    assert data["tools"][0]["component_type"] == "ServerTool"
    assert data["tools"][0]["name"] == oa_agent.tools[0].name
