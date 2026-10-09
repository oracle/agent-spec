# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""OCI Generative AI models in the OpenAI Agents adapter, through the OpenAI-compatible API."""

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from pyagentspec import Agent
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey
from pyagentspec.llms.ocigenaiconfig import (
    ModelProvider,
    OciAPIType,
    OciGenAiConfig,
    ServingMode,
)
from pyagentspec.retrypolicy import RetryPolicy

from ..conftest import OCI_TEST_API_KEY_PROFILE as PROFILE
from ..conftest import OCI_TEST_COMPARTMENT_ID as COMPARTMENT_ID
from ..conftest import OCI_TEST_SERVICE_ENDPOINT as SERVICE_ENDPOINT

pytest.importorskip("oci_genai_auth")

MODEL_ID = "openai.gpt-4.1"

CHAT_COMPLETION_RESPONSE: Dict[str, Any] = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 0,
    "model": MODEL_ID,
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}
    ],
}

RESPONSES_RESPONSE: Dict[str, Any] = {
    "id": "resp_test",
    "object": "response",
    "created_at": 0,
    "model": MODEL_ID,
    "status": "completed",
    "output": [
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "pong", "annotations": []}],
        }
    ],
    "parallel_tool_calls": True,
    "tool_choice": "auto",
    "tools": [],
}


def _client_config(config_file: Path) -> OciClientConfigWithApiKey:
    return OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=SERVICE_ENDPOINT,
        auth_file_location=str(config_file),
        auth_profile=PROFILE,
    )


def _llm_config(config_file: Path, **overrides: Any) -> OciGenAiConfig:
    # ``model_construct`` keeps these offline tests runnable when the test session patches the
    # constructors of LLM configurations to skip LLM-dependent tests (SKIP_LLM_TESTS=1).
    fields: Dict[str, Any] = dict(
        name="oci_llm",
        model_id=MODEL_ID,
        compartment_id=COMPARTMENT_ID,
        client_config=_client_config(config_file),
    )
    fields.update(overrides)
    return OciGenAiConfig.model_construct(**fields)


def _convert(llm_config: OciGenAiConfig) -> Any:
    from pyagentspec.adapters.openaiagents._openaiagentsconverter import (
        AgentSpecToOpenAIConverter,
    )

    return AgentSpecToOpenAIConverter().convert(llm_config, tool_registry={})


def _assert_oci_client(client: Any) -> None:
    import oci_genai_auth

    from pyagentspec.adapters._oci_openai_common import OCI_OPENAI_PLACEHOLDER_API_KEY

    assert str(client.base_url) == SERVICE_ENDPOINT + "/openai/v1/"
    assert client.api_key == OCI_OPENAI_PLACEHOLDER_API_KEY
    assert client._client.headers["opc-compartment-id"] == COMPARTMENT_ID
    assert client._client.headers["accept-encoding"] == "gzip, deflate"
    assert isinstance(client._client.auth, oci_genai_auth.OciUserPrincipalAuth)


@pytest.mark.parametrize("api_type", [OciAPIType.OCI, OciAPIType.OPENAI_CHAT_COMPLETIONS])
def test_oci_config_converts_to_chat_completions_model(
    oci_config_file: Path, api_type: OciAPIType
) -> None:
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

    model = _convert(_llm_config(oci_config_file, api_type=api_type))
    assert isinstance(model, OpenAIChatCompletionsModel)
    assert model.model == MODEL_ID
    _assert_oci_client(model._client)


def test_oci_config_with_responses_api_converts_to_responses_model(
    oci_config_file: Path,
) -> None:
    from agents.models.openai_responses import OpenAIResponsesModel

    model = _convert(_llm_config(oci_config_file, api_type=OciAPIType.OPENAI_RESPONSES))
    assert isinstance(model, OpenAIResponsesModel)
    assert model.model == MODEL_ID
    _assert_oci_client(model._client)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"provider": ModelProvider.COHERE}, "does not serve Cohere models"),
        ({"model_id": "cohere.command-a-03-2025"}, "does not serve Cohere models"),
        ({"serving_mode": ServingMode.DEDICATED}, "DEDICATED serving mode"),
    ],
)
def test_unsupported_oci_configs_are_rejected(
    oci_config_file: Path, overrides: Dict[str, Any], message: str
) -> None:
    with pytest.raises(NotImplementedError, match=message):
        _convert(_llm_config(oci_config_file, **overrides))


def test_retry_policy_maps_to_client_retries_and_timeout(oci_config_file: Path) -> None:
    model = _convert(
        _llm_config(oci_config_file, retry_policy=RetryPolicy(max_attempts=3, request_timeout=20))
    )
    assert model._client.max_retries == 3
    assert model._client.timeout == 20


def _install_mock_transport(
    monkeypatch: pytest.MonkeyPatch, payload: Dict[str, Any]
) -> List[httpx.Request]:
    """Route the signed OCI requests to a mock transport and record them."""
    from pyagentspec.adapters import _oci_openai_common

    recorded: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=payload)

    original = _oci_openai_common.create_oci_openai_httpx_client

    def with_mock_transport(llm_config: Any, *, is_async: bool, **kwargs: Any) -> Any:
        return original(
            llm_config, is_async=is_async, transport=httpx.MockTransport(handler), **kwargs
        )

    monkeypatch.setattr(_oci_openai_common, "create_oci_openai_httpx_client", with_mock_transport)
    return recorded


def _assert_signed_request(request: httpx.Request, path: str) -> None:
    assert request.url.host == "inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    assert request.url.path == path
    assert request.headers["authorization"].startswith("Signature ")
    assert request.headers["opc-compartment-id"] == COMPARTMENT_ID
    assert request.headers["accept-encoding"] == "gzip, deflate"
    assert "x-content-sha256" in request.headers
    assert json.loads(request.content)["model"] == MODEL_ID


@pytest.mark.anyio
@pytest.mark.parametrize(
    "api_type, payload, path",
    [
        (
            OciAPIType.OPENAI_CHAT_COMPLETIONS,
            CHAT_COMPLETION_RESPONSE,
            "/openai/v1/chat/completions",
        ),
        (OciAPIType.OPENAI_RESPONSES, RESPONSES_RESPONSE, "/openai/v1/responses"),
    ],
)
async def test_agent_runs_against_the_signed_oci_endpoint(
    oci_config_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    api_type: OciAPIType,
    payload: Dict[str, Any],
    path: str,
) -> None:
    from agents import Runner, set_tracing_disabled

    from pyagentspec.adapters.openaiagents import AgentSpecLoader

    set_tracing_disabled(True)
    recorded = _install_mock_transport(monkeypatch, payload)

    agent = Agent(
        name="assistant",
        llm_config=_llm_config(oci_config_file, api_type=api_type),
        system_prompt="You answer with one word.",
    )
    oa_agent = AgentSpecLoader(tool_registry={}).load_component(agent)

    result = await Runner.run(oa_agent, "ping")

    assert result.final_output == "pong"
    assert len(recorded) == 1
    _assert_signed_request(recorded[0], path)


def test_oci_model_converts_back_to_oci_config(oci_config_file: Path) -> None:
    """Round trip config -> model -> config.

    Builds the configuration with the regular constructor, so the test is skipped when the
    session patches LLM configuration constructors (SKIP_LLM_TESTS=1).
    """
    from pyagentspec.adapters.openaiagents._agentspecconverter import OpenAIToAgentSpecConverter

    llm_config = OciGenAiConfig(
        name="oci_llm",
        model_id=MODEL_ID,
        compartment_id=COMPARTMENT_ID,
        client_config=_client_config(oci_config_file),
        api_type=OciAPIType.OPENAI_RESPONSES,
        conversation_store_id="ocid1.store.oc1..aaaaaaaafakestore",
    )
    model = _convert(llm_config)

    rebuilt = OpenAIToAgentSpecConverter().convert(model)

    assert isinstance(rebuilt, OciGenAiConfig)
    assert rebuilt.model_id == MODEL_ID
    assert rebuilt.compartment_id == COMPARTMENT_ID
    assert rebuilt.api_type == OciAPIType.OPENAI_RESPONSES
    assert rebuilt.conversation_store_id == "ocid1.store.oc1..aaaaaaaafakestore"
    assert isinstance(rebuilt.client_config, OciClientConfigWithApiKey)
    assert rebuilt.client_config.service_endpoint == SERVICE_ENDPOINT
    assert rebuilt.client_config.auth_profile == PROFILE
    assert rebuilt.client_config.auth_file_location == str(oci_config_file)


def test_flow_code_generation_rejects_oci_configs(oci_config_file: Path) -> None:
    from pyagentspec.adapters.openaiagents import AgentSpecLoader
    from pyagentspec.adapters.openaiagents.flows import UnsupportedPatternError

    agent = Agent(
        name="assistant",
        llm_config=_llm_config(oci_config_file),
        system_prompt="You are helpful.",
    )
    start = StartNode(name="start")
    agent_node = AgentNode(name="agent_node", agent=agent)
    end = EndNode(name="end")
    flow = Flow(
        name="flow",
        start_node=start,
        nodes=[start, agent_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_agent", from_node=start, to_node=agent_node),
            ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end),
        ],
    )

    with pytest.raises(UnsupportedPatternError, match="does not support OciGenAiConfig") as e:
        AgentSpecLoader().load_component(flow)
    assert e.value.code == "OCI_LLM_CONFIG_UNSUPPORTED"
