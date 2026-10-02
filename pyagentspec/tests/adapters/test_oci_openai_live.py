# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""Live checks of the OpenAI-compatible API of OCI Generative AI (opt-in, needs credentials).

Enable with::

    OCI_OPENAI_TEST_PROFILE=<profile in ~/.oci/config> \\
    OCI_OPENAI_TEST_COMPARTMENT_ID=<compartment OCID> \\
    [OCI_OPENAI_TEST_REGION=us-chicago-1] [OCI_OPENAI_TEST_MODEL=openai.gpt-4.1] \\
    pytest tests/adapters/test_oci_openai_live.py

Profiles with a ``security_token_file`` use session-token authentication, other profiles use
API-key authentication.
"""

import json
import os
from typing import Any, Dict

import pytest

from pyagentspec.llms.ociclientconfig import (
    OciClientConfig,
    OciClientConfigWithApiKey,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.llms.ocigenaiconfig import OciAPIType, OciGenAiConfig

PROFILE = os.environ.get("OCI_OPENAI_TEST_PROFILE")
COMPARTMENT_ID = os.environ.get("OCI_OPENAI_TEST_COMPARTMENT_ID")
REGION = os.environ.get("OCI_OPENAI_TEST_REGION", "us-chicago-1")
MODEL_ID = os.environ.get("OCI_OPENAI_TEST_MODEL", "openai.gpt-4.1")
CONFIG_FILE = os.path.expanduser(os.environ.get("OCI_CONFIG_FILE", "~/.oci/config"))

pytestmark = pytest.mark.skipif(
    not PROFILE or not COMPARTMENT_ID,
    reason="OCI_OPENAI_TEST_PROFILE and OCI_OPENAI_TEST_COMPARTMENT_ID are not set",
)

# Imported at collection time: importing the OCI SDK reads platform files that the per-test
# file-access guard does not allow.
pytest.importorskip("oci_genai_auth")

MULTIPLY_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "multiply",
        "description": "Multiply two integers",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
}


def _client_config() -> OciClientConfig:
    import oci

    profile = oci.config.from_file(CONFIG_FILE, PROFILE)
    service_endpoint = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"
    if profile.get("security_token_file"):
        return OciClientConfigWithSecurityToken(
            name="client_config",
            service_endpoint=service_endpoint,
            auth_file_location=CONFIG_FILE,
            auth_profile=PROFILE,  # type: ignore[arg-type]
        )
    return OciClientConfigWithApiKey(
        name="client_config",
        service_endpoint=service_endpoint,
        auth_file_location=CONFIG_FILE,
        auth_profile=PROFILE,  # type: ignore[arg-type]
    )


@pytest.fixture
def llm_config() -> OciGenAiConfig:
    return OciGenAiConfig(
        name="oci_llm",
        model_id=MODEL_ID,
        compartment_id=COMPARTMENT_ID,  # type: ignore[arg-type]
        client_config=_client_config(),
        api_type=OciAPIType.OPENAI_CHAT_COMPLETIONS,
    )


def test_chat_completion_and_tool_call(llm_config: OciGenAiConfig) -> None:
    from pyagentspec.adapters._oci_openai_common import create_oci_openai_client

    client = create_oci_openai_client(llm_config, is_async=False)
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
        max_tokens=20,
    )
    assert "pong" in (completion.choices[0].message.content or "").lower()

    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": "What is 6 times 7? Use the tool."}],
        tools=[MULTIPLY_TOOL],
        max_tokens=100,
    )
    tool_calls = completion.choices[0].message.tool_calls or []
    assert [call.function.name for call in tool_calls] == ["multiply"]
    arguments = json.loads(tool_calls[0].function.arguments)
    assert {int(arguments["a"]), int(arguments["b"])} == {6, 7}


def test_streaming_is_decoded(llm_config: OciGenAiConfig) -> None:
    # Fails with "cannot use a decompressobj multiple times" when zstd is negotiated
    from pyagentspec.adapters._oci_openai_common import create_oci_openai_client

    client = create_oci_openai_client(llm_config, is_async=False)
    chunks = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": "Count from 1 to 5 separated by spaces"}],
        stream=True,
        max_tokens=30,
    )
    text = "".join(chunk.choices[0].delta.content or "" for chunk in chunks if chunk.choices)
    assert "1" in text and "5" in text


@pytest.mark.anyio
async def test_async_chat_completion(llm_config: OciGenAiConfig) -> None:
    from pyagentspec.adapters._oci_openai_common import create_oci_openai_client

    client = create_oci_openai_client(llm_config, is_async=True)
    completion = await client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
        max_tokens=20,
    )
    assert "pong" in (completion.choices[0].message.content or "").lower()
