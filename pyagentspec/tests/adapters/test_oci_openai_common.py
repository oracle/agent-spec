# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""OCI Generative AI through the OpenAI-compatible API: signed ``openai`` clients, no network."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import httpx
import pytest

from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithInstancePrincipal,
    OciClientConfigWithResourcePrincipal,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.llms.ocigenaiconfig import (
    ModelProvider,
    OciAPIType,
    OciGenAiConfig,
    ServingMode,
)
from pyagentspec.retrypolicy import RetryPolicy

from ..adapters.conftest import OCI_TEST_API_KEY_PROFILE as API_KEY_PROFILE
from ..adapters.conftest import OCI_TEST_COMPARTMENT_ID as COMPARTMENT_ID
from ..adapters.conftest import OCI_TEST_SERVICE_ENDPOINT as SERVICE_ENDPOINT
from ..adapters.conftest import OCI_TEST_SESSION_PROFILE as SESSION_PROFILE

pytest.importorskip("oci_genai_auth")

try:
    from pyagentspec.llms.ociclientconfig import OciClientConfigWithGenAiApiKey

    GENAI_API_KEY_COMPONENT_AVAILABLE = True
except ImportError:
    # The component ships with a separate Agent Spec change (issue #265). Until it lands, a
    # stand-in with the `auth_type` discriminator of the specification exercises the helper.
    GENAI_API_KEY_COMPONENT_AVAILABLE = False

    class OciClientConfigWithGenAiApiKey(OciClientConfig):  # type: ignore[no-redef]
        auth_type: Literal["GENAI_API_KEY"] = "GENAI_API_KEY"  # type: ignore[assignment]
        api_key: Optional[str] = None


from pyagentspec.adapters._oci_openai_common import (  # noqa: E402
    COMPARTMENT_ID_HEADER,
    CONVERSATION_STORE_ID_HEADER,
    OCI_GENAI_API_KEY_ENV_VAR,
    OCI_OPENAI_ACCEPT_ENCODING,
    OCI_OPENAI_PLACEHOLDER_API_KEY,
    create_oci_httpx_auth,
    create_oci_openai_client,
    ensure_oci_openai_installed,
    get_oci_openai_base_url,
    get_oci_openai_headers,
    get_oci_openai_retry_kwargs,
    is_oci_openai_base_url,
    oci_genai_config_from_openai_client,
    validate_oci_openai_compatible_config,
)

CHAT_COMPLETION_RESPONSE: Dict[str, Any] = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 0,
    "model": "openai.gpt-4.1",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}
    ],
}


def _api_key_client_config(config_file: Path) -> OciClientConfigWithApiKey:
    return OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=SERVICE_ENDPOINT,
        auth_file_location=str(config_file),
        auth_profile=API_KEY_PROFILE,
    )


def _session_client_config(config_file: Path) -> OciClientConfigWithSecurityToken:
    return OciClientConfigWithSecurityToken(
        name="client_config",
        service_endpoint=SERVICE_ENDPOINT,
        auth_file_location=str(config_file),
        auth_profile=SESSION_PROFILE,
    )


def _genai_api_key_client_config(
    api_key: Optional[str] = "sk-test-key",
) -> OciClientConfigWithGenAiApiKey:
    return OciClientConfigWithGenAiApiKey(
        name="client_config", service_endpoint=SERVICE_ENDPOINT, api_key=api_key
    )


def _llm_config(client_config: Any, **overrides: Any) -> OciGenAiConfig:
    # ``model_construct`` keeps these unit tests runnable when the test session patches the
    # constructors of LLM configurations to skip LLM-dependent tests (SKIP_LLM_TESTS=1): no
    # model is ever called here.
    fields: Dict[str, Any] = dict(
        name="oci_llm",
        model_id="openai.gpt-4.1",
        compartment_id=COMPARTMENT_ID,
        client_config=client_config,
    )
    fields.update(overrides)
    return OciGenAiConfig.model_construct(**fields)


def _mock_transport(recorded: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=CHAT_COMPLETION_RESPONSE)

    return httpx.MockTransport(handler)


def test_base_url_is_the_openai_path_of_the_service_endpoint(oci_config_file: Path) -> None:
    llm_config = _llm_config(_api_key_client_config(oci_config_file))
    assert get_oci_openai_base_url(llm_config) == SERVICE_ENDPOINT + "/openai/v1"
    # A trailing slash in the endpoint does not double up
    llm_config.client_config.service_endpoint = SERVICE_ENDPOINT + "/"
    assert get_oci_openai_base_url(llm_config) == SERVICE_ENDPOINT + "/openai/v1"
    assert is_oci_openai_base_url(SERVICE_ENDPOINT + "/openai/v1/")
    assert not is_oci_openai_base_url("https://api.openai.com/v1")


def test_headers_carry_compartment_conversation_store_and_encoding(
    oci_config_file: Path,
) -> None:
    llm_config = _llm_config(_api_key_client_config(oci_config_file))
    assert get_oci_openai_headers(llm_config) == {
        COMPARTMENT_ID_HEADER: COMPARTMENT_ID,
        "Accept-Encoding": OCI_OPENAI_ACCEPT_ENCODING,
    }
    llm_config = _llm_config(
        _api_key_client_config(oci_config_file), conversation_store_id="ocid1.store.oc1..x"
    )
    assert get_oci_openai_headers(llm_config)[CONVERSATION_STORE_ID_HEADER] == "ocid1.store.oc1..x"


def test_auth_is_created_from_each_client_config_type(
    oci_config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    oci_genai_auth = ensure_oci_openai_installed()

    session_auth = create_oci_httpx_auth(_session_client_config(oci_config_file))
    assert isinstance(session_auth, oci_genai_auth.OciSessionAuth)
    assert session_auth.profile_name == SESSION_PROFILE

    api_key_auth = create_oci_httpx_auth(_api_key_client_config(oci_config_file))
    assert isinstance(api_key_auth, oci_genai_auth.OciUserPrincipalAuth)
    assert api_key_auth.profile_name == API_KEY_PROFILE

    # Principal-based authentications contact the OCI metadata service, so they are replaced
    class _FakeAuth(httpx.Auth):
        def __init__(self) -> None:
            self.created = True

    monkeypatch.setattr(oci_genai_auth, "OciInstancePrincipalAuth", _FakeAuth)
    monkeypatch.setattr(oci_genai_auth, "OciResourcePrincipalAuth", _FakeAuth)
    instance_principal = OciClientConfigWithInstancePrincipal(
        name="client_config", service_endpoint=SERVICE_ENDPOINT
    )
    resource_principal = OciClientConfigWithResourcePrincipal(
        name="client_config", service_endpoint=SERVICE_ENDPOINT
    )
    assert isinstance(create_oci_httpx_auth(instance_principal), _FakeAuth)
    assert isinstance(create_oci_httpx_auth(resource_principal), _FakeAuth)


def test_missing_oci_openai_package_raises_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "oci_genai_auth", None)
    with pytest.raises(ImportError, match="pip install oci-genai-auth"):
        ensure_oci_openai_installed()


def test_retry_policy_maps_to_client_retries_and_timeout() -> None:
    assert get_oci_openai_retry_kwargs(None) == {}
    assert get_oci_openai_retry_kwargs(RetryPolicy(max_attempts=5)) == {"max_retries": 5}
    assert get_oci_openai_retry_kwargs(RetryPolicy(max_attempts=1, request_timeout=30.0)) == {
        "max_retries": 1,
        "timeout": 30.0,
    }


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"serving_mode": ServingMode.DEDICATED}, "DEDICATED serving mode"),
        ({"provider": ModelProvider.COHERE}, "does not serve Cohere models"),
        ({"model_id": "cohere.command-a-03-2025"}, "does not serve Cohere models"),
        ({"api_type": OciAPIType.OPENAI_RESPONSES}, "does not support the OpenAI Responses API"),
    ],
)
def test_unsupported_configurations_are_rejected_early(
    oci_config_file: Path, overrides: Dict[str, Any], message: str
) -> None:
    llm_config = _llm_config(_api_key_client_config(oci_config_file), **overrides)
    with pytest.raises(NotImplementedError, match=message):
        validate_oci_openai_compatible_config(
            llm_config, runtime_name="TestRuntime", responses_api_supported=False
        )


def test_supported_configurations_pass_validation(oci_config_file: Path) -> None:
    client_config = _api_key_client_config(oci_config_file)
    for api_type in (OciAPIType.OCI, OciAPIType.OPENAI_CHAT_COMPLETIONS):
        validate_oci_openai_compatible_config(
            _llm_config(client_config, api_type=api_type),
            runtime_name="TestRuntime",
            responses_api_supported=False,
        )
    validate_oci_openai_compatible_config(
        _llm_config(client_config, api_type=OciAPIType.OPENAI_RESPONSES),
        runtime_name="TestRuntime",
        responses_api_supported=True,
    )


def _assert_signed_oci_request(request: httpx.Request, key_id_prefix: str) -> None:
    assert request.url.host == "inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    assert request.url.path == "/openai/v1/chat/completions"
    authorization = request.headers["authorization"]
    assert authorization.startswith("Signature ")
    assert f'keyId="{key_id_prefix}' in authorization
    assert "x-content-sha256" in request.headers
    assert "date" in request.headers
    assert request.headers[COMPARTMENT_ID_HEADER] == COMPARTMENT_ID
    assert request.headers["accept-encoding"] == OCI_OPENAI_ACCEPT_ENCODING
    assert json.loads(request.content)["model"] == "openai.gpt-4.1"


def test_sync_client_signs_requests_with_api_key(oci_config_file: Path) -> None:
    recorded: list[httpx.Request] = []
    llm_config = _llm_config(
        _api_key_client_config(oci_config_file),
        retry_policy=RetryPolicy(max_attempts=0, request_timeout=12.5),
    )
    client = create_oci_openai_client(
        llm_config, is_async=False, transport=_mock_transport(recorded)
    )
    assert client.api_key == OCI_OPENAI_PLACEHOLDER_API_KEY
    assert str(client.base_url) == SERVICE_ENDPOINT + "/openai/v1/"
    assert client.max_retries == 0
    assert client.timeout == 12.5

    completion = client.chat.completions.create(
        model="openai.gpt-4.1", messages=[{"role": "user", "content": "ping"}]
    )
    assert completion.choices[0].message.content == "pong"
    assert len(recorded) == 1
    _assert_signed_oci_request(
        recorded[0], key_id_prefix="ocid1.tenancy.oc1..aaaaaaaafaketenancy/ocid1.user"
    )


@pytest.mark.anyio
async def test_async_client_signs_requests_with_session_token(oci_config_file: Path) -> None:
    recorded: list[httpx.Request] = []
    llm_config = _llm_config(_session_client_config(oci_config_file))
    client = create_oci_openai_client(
        llm_config, is_async=True, transport=_mock_transport(recorded)
    )

    completion = await client.chat.completions.create(
        model="openai.gpt-4.1", messages=[{"role": "user", "content": "ping"}]
    )
    assert completion.choices[0].message.content == "pong"
    assert len(recorded) == 1
    # Session tokens are referenced with the ST$ prefix in the signature key id
    _assert_signed_oci_request(recorded[0], key_id_prefix="ST$fake-session-token")


def test_config_is_rebuilt_from_an_oci_openai_client(oci_config_file: Path) -> None:
    llm_config = _llm_config(
        _session_client_config(oci_config_file), conversation_store_id="ocid1.store.oc1..x"
    )
    client = create_oci_openai_client(llm_config, is_async=True)

    rebuilt = oci_genai_config_from_openai_client(
        client, name="rebuilt", model_id="openai.gpt-4.1", api_type=OciAPIType.OPENAI_RESPONSES
    )
    assert rebuilt is not None
    assert rebuilt.model_id == "openai.gpt-4.1"
    assert rebuilt.compartment_id == COMPARTMENT_ID
    assert rebuilt.api_type == OciAPIType.OPENAI_RESPONSES
    assert rebuilt.conversation_store_id == "ocid1.store.oc1..x"
    assert isinstance(rebuilt.client_config, OciClientConfigWithSecurityToken)
    assert rebuilt.client_config.service_endpoint == SERVICE_ENDPOINT
    assert rebuilt.client_config.auth_profile == SESSION_PROFILE
    assert rebuilt.client_config.auth_file_location == str(oci_config_file)


def test_non_oci_client_is_not_converted() -> None:
    from openai import OpenAI

    client = OpenAI(api_key="sk-test", base_url="https://api.openai.com/v1")
    assert (
        oci_genai_config_from_openai_client(
            client, name="x", model_id="gpt-4.1", api_type=OciAPIType.OPENAI_CHAT_COMPLETIONS
        )
        is None
    )


def _assert_bearer_oci_request(request: httpx.Request, api_key: str) -> None:
    assert request.url.host == "inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    assert request.url.path == "/openai/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {api_key}"
    # No OCI request signature
    assert "x-content-sha256" not in request.headers
    assert request.headers[COMPARTMENT_ID_HEADER] == COMPARTMENT_ID
    assert request.headers["accept-encoding"] == OCI_OPENAI_ACCEPT_ENCODING


def test_genai_api_key_client_sends_a_bearer_token_without_request_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Generative AI API keys do not need the `oci-genai-auth` package at all
    monkeypatch.setitem(sys.modules, "oci_genai_auth", None)
    recorded: list[httpx.Request] = []
    llm_config = _llm_config(
        _genai_api_key_client_config("sk-test-key"), retry_policy=RetryPolicy(max_attempts=2)
    )
    client = create_oci_openai_client(
        llm_config, is_async=False, transport=_mock_transport(recorded)
    )
    assert client.api_key == "sk-test-key"
    assert str(client.base_url) == SERVICE_ENDPOINT + "/openai/v1/"
    assert client.max_retries == 2

    completion = client.chat.completions.create(
        model="meta.llama-3.3-70b-instruct", messages=[{"role": "user", "content": "ping"}]
    )
    assert completion.choices[0].message.content == "pong"
    assert len(recorded) == 1
    _assert_bearer_oci_request(recorded[0], "sk-test-key")


@pytest.mark.anyio
async def test_async_genai_api_key_client_sends_a_bearer_token() -> None:
    recorded: list[httpx.Request] = []
    llm_config = _llm_config(_genai_api_key_client_config("sk-test-key"))
    client = create_oci_openai_client(
        llm_config, is_async=True, transport=_mock_transport(recorded)
    )
    completion = await client.chat.completions.create(
        model="meta.llama-3.3-70b-instruct", messages=[{"role": "user", "content": "ping"}]
    )
    assert completion.choices[0].message.content == "pong"
    _assert_bearer_oci_request(recorded[0], "sk-test-key")


def test_genai_api_key_is_read_from_the_environment_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm_config = _llm_config(_genai_api_key_client_config(api_key=None))
    monkeypatch.setenv(OCI_GENAI_API_KEY_ENV_VAR, "sk-from-env")
    client = create_oci_openai_client(llm_config, is_async=False, transport=_mock_transport([]))
    assert client.api_key == "sk-from-env"

    monkeypatch.delenv(OCI_GENAI_API_KEY_ENV_VAR)
    with pytest.raises(ValueError, match=OCI_GENAI_API_KEY_ENV_VAR):
        create_oci_openai_client(llm_config, is_async=False)


def test_genai_api_key_config_cannot_create_a_signing_auth() -> None:
    with pytest.raises(ValueError, match="bearer token"):
        create_oci_httpx_auth(_genai_api_key_client_config())


def test_genai_api_key_client_maps_back_without_the_key() -> None:
    llm_config = _llm_config(
        _genai_api_key_client_config("sk-test-key"), conversation_store_id="ocid1.store.oc1..x"
    )
    client = create_oci_openai_client(llm_config, is_async=False)
    rebuilt = oci_genai_config_from_openai_client(
        client,
        name="oci_llm",
        model_id="meta.llama-3.3-70b-instruct",
        api_type=OciAPIType.OPENAI_CHAT_COMPLETIONS,
    )
    if not GENAI_API_KEY_COMPONENT_AVAILABLE:
        # Older Agent Spec versions have no component for this configuration
        assert rebuilt is None
        return
    assert rebuilt is not None
    assert isinstance(rebuilt.client_config, OciClientConfigWithGenAiApiKey)
    assert rebuilt.client_config.api_key is None
    assert rebuilt.client_config.service_endpoint == SERVICE_ENDPOINT
    assert rebuilt.compartment_id == COMPARTMENT_ID
    assert rebuilt.conversation_store_id == "ocid1.store.oc1..x"
    assert "sk-test-key" not in rebuilt.to_json()
