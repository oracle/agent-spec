# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""OCI Generative AI configurations run on Agent Framework through the OpenAI-compatible API.

No network: requests are captured with an ``httpx`` mock transport, and the OCI credentials
come from a generated configuration file.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from pyagentspec.llms.ociclientconfig import OciClientConfigWithApiKey
from pyagentspec.llms.ocigenaiconfig import ModelProvider, OciAPIType, OciGenAiConfig, ServingMode
from pyagentspec.retrypolicy import RetryPolicy

from ..conftest import OCI_TEST_API_KEY_PROFILE as API_KEY_PROFILE
from ..conftest import OCI_TEST_COMPARTMENT_ID as COMPARTMENT_ID
from ..conftest import OCI_TEST_SERVICE_ENDPOINT as SERVICE_ENDPOINT

# Imported at collection time: importing the OCI SDK reads platform files that the per-test
# file-access guard does not allow.
pytest.importorskip("oci_genai_auth")

from pyagentspec.adapters import _oci_openai_common  # noqa: E402
from pyagentspec.adapters._oci_openai_common import (  # noqa: E402
    COMPARTMENT_ID_HEADER,
    OCI_OPENAI_ACCEPT_ENCODING,
    OCI_OPENAI_PLACEHOLDER_API_KEY,
)

MODEL_ID = "openai.gpt-4.1"

CHAT_COMPLETION_RESPONSE: Dict[str, Any] = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 0,
    "model": MODEL_ID,
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}

RESPONSES_API_RESPONSE: Dict[str, Any] = {
    "id": "resp_test",
    "object": "response",
    "created_at": 0,
    "status": "completed",
    "model": MODEL_ID,
    "output": [
        {
            "type": "message",
            "id": "msg_test",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "pong", "annotations": []}],
        }
    ],
    "parallel_tool_calls": True,
    "tool_choice": "auto",
    "tools": [],
    "usage": {
        "input_tokens": 1,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens": 1,
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": 2,
    },
}


def _client_config(config_file: Path) -> OciClientConfigWithApiKey:
    return OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=SERVICE_ENDPOINT,
        auth_file_location=str(config_file),
        auth_profile=API_KEY_PROFILE,
    )


def _llm_config(config_file: Path, **overrides: Any) -> OciGenAiConfig:
    # ``model_construct`` keeps these tests runnable when the test session patches the
    # constructors of LLM configurations to skip LLM-dependent tests (SKIP_LLM_TESTS=1): no
    # model is ever called here.
    fields: Dict[str, Any] = dict(
        name="oci_llm",
        model_id=MODEL_ID,
        compartment_id=COMPARTMENT_ID,
        client_config=_client_config(config_file),
    )
    fields.update(overrides)
    return OciGenAiConfig.model_construct(**fields)


@pytest.fixture
def recorded_requests(monkeypatch: pytest.MonkeyPatch) -> List[httpx.Request]:
    """Route the signed requests of the OCI clients to a mock transport and record them."""
    recorded: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        if request.url.path.endswith("/responses"):
            return httpx.Response(200, json=RESPONSES_API_RESPONSE)
        return httpx.Response(200, json=CHAT_COMPLETION_RESPONSE)

    original = _oci_openai_common.create_oci_openai_httpx_client

    def with_mock_transport(llm_config: OciGenAiConfig, *, is_async: bool, **kwargs: Any) -> Any:
        return original(
            llm_config, is_async=is_async, transport=httpx.MockTransport(handler), **kwargs
        )

    monkeypatch.setattr(_oci_openai_common, "create_oci_openai_httpx_client", with_mock_transport)
    return recorded


@pytest.mark.parametrize(
    ("api_type", "expected_client_name"),
    [
        (OciAPIType.OCI, "OpenAIChatCompletionClient"),
        (OciAPIType.OPENAI_CHAT_COMPLETIONS, "OpenAIChatCompletionClient"),
        (OciAPIType.OPENAI_RESPONSES, "OpenAIChatClient"),
    ],
)
def test_oci_config_converts_to_a_signed_openai_client(
    oci_config_file: Path, api_type: OciAPIType, expected_client_name: str
) -> None:
    import oci_genai_auth
    from agent_framework.openai import OpenAIChatClient, OpenAIChatCompletionClient

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    chat_client = AgentSpecLoader().load_component(_llm_config(oci_config_file, api_type=api_type))

    expected_client = {
        "OpenAIChatClient": OpenAIChatClient,
        "OpenAIChatCompletionClient": OpenAIChatCompletionClient,
    }[expected_client_name]
    assert isinstance(chat_client, expected_client)
    assert chat_client.model == MODEL_ID

    openai_client = chat_client.client
    assert str(openai_client.base_url) == SERVICE_ENDPOINT + "/openai/v1/"
    assert openai_client.api_key == OCI_OPENAI_PLACEHOLDER_API_KEY
    http_client = openai_client._client
    assert http_client.headers[COMPARTMENT_ID_HEADER] == COMPARTMENT_ID
    assert http_client.headers["accept-encoding"] == OCI_OPENAI_ACCEPT_ENCODING
    assert isinstance(http_client.auth, oci_genai_auth.OciUserPrincipalAuth)


def test_retry_policy_configures_the_openai_client(oci_config_file: Path) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    chat_client = AgentSpecLoader().load_component(
        _llm_config(oci_config_file, retry_policy=RetryPolicy(max_attempts=3, request_timeout=20.0))
    )
    assert chat_client.client.max_retries == 3
    assert chat_client.client.timeout == 20.0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"serving_mode": ServingMode.DEDICATED}, "DEDICATED serving mode"),
        ({"provider": ModelProvider.COHERE}, "does not serve Cohere models"),
        ({"model_id": "cohere.command-a-03-2025"}, "does not serve Cohere models"),
    ],
)
def test_configurations_the_openai_compatible_api_cannot_serve_are_rejected(
    oci_config_file: Path, overrides: Dict[str, Any], message: str
) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    with pytest.raises(NotImplementedError, match=message):
        AgentSpecLoader().load_component(_llm_config(oci_config_file, **overrides))


def _assert_signed_oci_request(request: httpx.Request, path: str) -> None:
    assert request.url.host == "inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    assert request.url.path == path
    authorization = request.headers["authorization"]
    assert authorization.startswith("Signature ")
    assert 'keyId="ocid1.tenancy.oc1..aaaaaaaafaketenancy/ocid1.user.oc1..aaaaaaaafakeuser/' in (
        authorization
    )
    assert "x-content-sha256" in request.headers
    assert request.headers[COMPARTMENT_ID_HEADER] == COMPARTMENT_ID
    assert request.headers["accept-encoding"] == OCI_OPENAI_ACCEPT_ENCODING
    assert json.loads(request.content)["model"] == MODEL_ID


@pytest.mark.anyio
async def test_agent_sends_signed_chat_completion_requests(
    oci_config_file: Path, recorded_requests: List[httpx.Request]
) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_component(_spec_agent(_llm_config(oci_config_file)))
    response = await agent.run("ping")

    assert "pong" in response.text
    assert len(recorded_requests) == 1
    _assert_signed_oci_request(recorded_requests[0], path="/openai/v1/chat/completions")


@pytest.mark.anyio
async def test_responses_client_sends_signed_responses_requests(
    oci_config_file: Path, recorded_requests: List[httpx.Request]
) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    chat_client = AgentSpecLoader().load_component(
        _llm_config(oci_config_file, api_type=OciAPIType.OPENAI_RESPONSES)
    )
    response = await chat_client.get_response("ping")

    assert "pong" in response.text
    assert len(recorded_requests) == 1
    _assert_signed_oci_request(recorded_requests[0], path="/openai/v1/responses")


def test_oci_client_converts_back_to_an_oci_config(oci_config_file: Path) -> None:
    # The round trip constructs an OciGenAiConfig through its constructor, so this test is
    # skipped when the session patches LLM configuration constructors (SKIP_LLM_TESTS=1).
    from pyagentspec.adapters.agent_framework import AgentSpecExporter, AgentSpecLoader

    llm_config = OciGenAiConfig(
        name="oci_llm",
        model_id=MODEL_ID,
        compartment_id=COMPARTMENT_ID,
        client_config=_client_config(oci_config_file),
        api_type=OciAPIType.OPENAI_RESPONSES,
        conversation_store_id="ocid1.store.oc1..aaaaaaaafakestore",
    )
    chat_client = AgentSpecLoader().load_component(llm_config)

    rebuilt = AgentSpecExporter().to_component(chat_client)

    assert isinstance(rebuilt, OciGenAiConfig)
    assert rebuilt.model_id == MODEL_ID
    assert rebuilt.compartment_id == COMPARTMENT_ID
    assert rebuilt.api_type == OciAPIType.OPENAI_RESPONSES
    assert rebuilt.conversation_store_id == "ocid1.store.oc1..aaaaaaaafakestore"
    assert isinstance(rebuilt.client_config, OciClientConfigWithApiKey)
    assert rebuilt.client_config.service_endpoint == SERVICE_ENDPOINT
    assert rebuilt.client_config.auth_profile == API_KEY_PROFILE
    assert rebuilt.client_config.auth_file_location == str(oci_config_file)


def _spec_agent(llm_config: OciGenAiConfig) -> Any:
    from pyagentspec.agent import Agent as AgentSpecAgent

    return AgentSpecAgent.model_construct(
        name="ping_agent",
        system_prompt="Answer with one word.",
        llm_config=llm_config,
        tools=[],
        toolboxes=[],
        transforms=[],
        inputs=[],
        outputs=[],
        metadata={},
    )


@pytest.mark.anyio
async def test_responses_agent_without_conversation_store_does_not_retain_responses(
    oci_config_file: Path, recorded_requests: List[httpx.Request]
) -> None:
    # OCI does not retain responses without a conversation store, so the agent must not chain
    # its turns with previous_response_id: the request asks the service not to store them
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_component(
        _spec_agent(_llm_config(oci_config_file, api_type=OciAPIType.OPENAI_RESPONSES))
    )
    response = await agent.run("ping")

    assert "pong" in response.text
    body = json.loads(recorded_requests[0].content)
    assert body["store"] is False
    assert "previous_response_id" not in body
    assert "opc-conversation-store-id" not in recorded_requests[0].headers


@pytest.mark.anyio
async def test_responses_agent_with_conversation_store_keeps_default_retention(
    oci_config_file: Path, recorded_requests: List[httpx.Request]
) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_component(
        _spec_agent(
            _llm_config(
                oci_config_file,
                api_type=OciAPIType.OPENAI_RESPONSES,
                conversation_store_id="ocid1.store.oc1..aaaaaaaafakestore",
            )
        )
    )
    await agent.run("ping")

    body = json.loads(recorded_requests[0].content)
    assert body.get("store") is not False
    assert (
        recorded_requests[0].headers["opc-conversation-store-id"]
        == "ocid1.store.oc1..aaaaaaaafakestore"
    )


@pytest.mark.anyio
async def test_chat_completions_agent_has_no_store_option(
    oci_config_file: Path, recorded_requests: List[httpx.Request]
) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_component(_spec_agent(_llm_config(oci_config_file)))
    await agent.run("ping")

    assert "store" not in json.loads(recorded_requests[0].content)
