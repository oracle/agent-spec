# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
from typing import Any

import pytest
from pydantic import ValidationError

from pyagentspec.llms import GeminiConfig
from pyagentspec.llms.geminiauthconfig import GeminiAIStudioAuthConfig, GeminiVertexAIAuthConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

GEMINI_CONFIG_ID = "gemini-config-id"
GEMINI_CONFIG_NAME = "gemini"
GEMINI_AISTUDIO_AUTH_ID = "gemini-aistudio-auth-id"
GEMINI_AISTUDIO_AUTH_NAME = "gemini-aistudio-auth"
GEMINI_VERTEX_AUTH_ID = "gemini-vertex-auth-id"
GEMINI_VERTEX_AUTH_NAME = "gemini-vertex-auth"


def _assert_serialized_geminiconfig_fields(
    serialized_llm_as_dict: dict[str, Any], *, model_id: str
) -> None:
    assert serialized_llm_as_dict["component_type"] == "GeminiConfig"
    assert serialized_llm_as_dict["id"] == GEMINI_CONFIG_ID
    assert serialized_llm_as_dict["name"] == GEMINI_CONFIG_NAME
    assert serialized_llm_as_dict["description"] is None
    assert serialized_llm_as_dict["metadata"] == {}
    assert serialized_llm_as_dict["default_generation_parameters"] is None
    assert serialized_llm_as_dict["model_id"] == model_id
    assert serialized_llm_as_dict["agentspec_version"] == AgentSpecVersionEnum.v26_2_0.value


@pytest.mark.parametrize(
    ("auth", "model_id", "expected_auth", "expected_auth_type"),
    [
        (
            GeminiAIStudioAuthConfig(
                id=GEMINI_AISTUDIO_AUTH_ID,
                name=GEMINI_AISTUDIO_AUTH_NAME,
            ),
            "gemini-2.5-flash",
            {
                "component_type": "GeminiAIStudioAuthConfig",
                "id": GEMINI_AISTUDIO_AUTH_ID,
                "name": GEMINI_AISTUDIO_AUTH_NAME,
                "description": None,
                "metadata": {},
                "api_key": None,
            },
            GeminiAIStudioAuthConfig,
        ),
        (
            GeminiVertexAIAuthConfig(
                id=GEMINI_VERTEX_AUTH_ID,
                name=GEMINI_VERTEX_AUTH_NAME,
            ),
            "gemini-2.0-flash-lite",
            {
                "component_type": "GeminiVertexAIAuthConfig",
                "id": GEMINI_VERTEX_AUTH_ID,
                "name": GEMINI_VERTEX_AUTH_NAME,
                "description": None,
                "metadata": {},
                "project_id": None,
                "location": "global",
                "credentials": None,
            },
            GeminiVertexAIAuthConfig,
        ),
        (
            GeminiVertexAIAuthConfig(
                id=GEMINI_VERTEX_AUTH_ID,
                name=GEMINI_VERTEX_AUTH_NAME,
                project_id="project-id",
                location="us-central1",
            ),
            "gemini-2.0-flash-lite",
            {
                "component_type": "GeminiVertexAIAuthConfig",
                "id": GEMINI_VERTEX_AUTH_ID,
                "name": GEMINI_VERTEX_AUTH_NAME,
                "description": None,
                "metadata": {},
                "project_id": "project-id",
                "location": "us-central1",
                "credentials": None,
            },
            GeminiVertexAIAuthConfig,
        ),
    ],
    ids=["aistudio-empty", "vertex-empty", "vertex-without-credentials"],
)
def test_can_serialize_and_deserialize_gemini_config_with_inline_auth(
    auth: GeminiAIStudioAuthConfig | GeminiVertexAIAuthConfig,
    model_id: str,
    expected_auth: dict[str, Any],
    expected_auth_type: type[object],
) -> None:
    llm_config = GeminiConfig(
        id=GEMINI_CONFIG_ID,
        name=GEMINI_CONFIG_NAME,
        model_id=model_id,
        auth=auth,
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    serialized_llm_as_dict = json.loads(serialized_llm)

    assert '"$component_ref"' not in serialized_llm
    _assert_serialized_geminiconfig_fields(serialized_llm_as_dict, model_id=model_id)
    assert serialized_llm_as_dict["auth"] == expected_auth

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert deserialized_llm == llm_config
    assert deserialized_llm.min_agentspec_version == AgentSpecVersionEnum.v26_2_0
    assert isinstance(deserialized_llm.auth, expected_auth_type)


@pytest.mark.parametrize(
    (
        "auth",
        "model_id",
        "expected_auth",
        "components_registry",
        "missing_component_ref",
        "hidden_values",
        "expected_auth_type",
    ),
    [
        (
            GeminiAIStudioAuthConfig(
                id=GEMINI_AISTUDIO_AUTH_ID,
                name=GEMINI_AISTUDIO_AUTH_NAME,
                api_key="THIS_IS_SECRET",
            ),
            "gemini-2.5-flash",
            {
                "component_type": "GeminiAIStudioAuthConfig",
                "id": GEMINI_AISTUDIO_AUTH_ID,
                "name": GEMINI_AISTUDIO_AUTH_NAME,
                "description": None,
                "metadata": {},
                "api_key": {"$component_ref": f"{GEMINI_AISTUDIO_AUTH_ID}.api_key"},
            },
            {f"{GEMINI_AISTUDIO_AUTH_ID}.api_key": "THIS_IS_SECRET"},
            rf"{GEMINI_AISTUDIO_AUTH_ID}\.api_key",
            ("THIS_IS_SECRET",),
            GeminiAIStudioAuthConfig,
        ),
        (
            GeminiVertexAIAuthConfig(
                id=GEMINI_VERTEX_AUTH_ID,
                name=GEMINI_VERTEX_AUTH_NAME,
                project_id="project-id",
                location="global",
                credentials={
                    "type": "service_account",
                    "client_email": "agent@example.com",
                    "private_key": "line1\\nline2",
                },
            ),
            "gemini-2.0-flash-lite",
            {
                "component_type": "GeminiVertexAIAuthConfig",
                "id": GEMINI_VERTEX_AUTH_ID,
                "name": GEMINI_VERTEX_AUTH_NAME,
                "description": None,
                "metadata": {},
                "project_id": "project-id",
                "location": "global",
                "credentials": {"$component_ref": f"{GEMINI_VERTEX_AUTH_ID}.credentials"},
            },
            {
                f"{GEMINI_VERTEX_AUTH_ID}.credentials": {
                    "type": "service_account",
                    "client_email": "agent@example.com",
                    "private_key": "line1\\nline2",
                },
            },
            rf"{GEMINI_VERTEX_AUTH_ID}\.credentials",
            ("service_account", "agent@example.com"),
            GeminiVertexAIAuthConfig,
        ),
    ],
    ids=["aistudio-api-key", "vertex-credentials"],
)
def test_can_serialize_and_deserialize_gemini_config_with_sensitive_auth_fields(
    auth: GeminiAIStudioAuthConfig | GeminiVertexAIAuthConfig,
    model_id: str,
    expected_auth: dict[str, Any],
    components_registry: dict[str, Any],
    missing_component_ref: str,
    hidden_values: tuple[str, ...],
    expected_auth_type: type[object],
) -> None:
    llm_config = GeminiConfig(
        id=GEMINI_CONFIG_ID,
        name=GEMINI_CONFIG_NAME,
        model_id=model_id,
        auth=auth,
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    serialized_llm_as_dict = json.loads(serialized_llm)

    for hidden_value in hidden_values:
        assert hidden_value not in serialized_llm

    _assert_serialized_geminiconfig_fields(serialized_llm_as_dict, model_id=model_id)
    assert serialized_llm_as_dict["auth"] == expected_auth

    with pytest.raises(ValueError, match=missing_component_ref):
        AgentSpecDeserializer().from_json(serialized_llm)

    deserialized_llm = AgentSpecDeserializer().from_json(
        serialized_llm,
        components_registry=components_registry,
    )

    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, expected_auth_type)


def test_geminiconfig_requires_auth() -> None:
    with pytest.raises(ValidationError, match="auth"):
        GeminiConfig(name=GEMINI_CONFIG_NAME, model_id="gemini-2.5-flash")


def test_can_deserialize_gemini_config_with_inline_vertex_auth_component() -> None:
    serialized_llm = json.dumps(
        {
            "component_type": "GeminiConfig",
            "id": GEMINI_CONFIG_ID,
            "name": GEMINI_CONFIG_NAME,
            "model_id": "gemini-2.0-flash-lite",
            "auth": {
                "component_type": "GeminiVertexAIAuthConfig",
                "id": GEMINI_VERTEX_AUTH_ID,
                "name": GEMINI_VERTEX_AUTH_NAME,
            },
            "agentspec_version": AgentSpecVersionEnum.v26_2_0.value,
        }
    )

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert isinstance(deserialized_llm, GeminiConfig)
    assert isinstance(deserialized_llm.auth, GeminiVertexAIAuthConfig)
    assert deserialized_llm.auth == GeminiVertexAIAuthConfig(
        id=GEMINI_VERTEX_AUTH_ID,
        name=GEMINI_VERTEX_AUTH_NAME,
    )


def test_deserializing_gemini_config_without_auth_raises_error() -> None:
    serialized_llm = json.dumps(
        {
            "component_type": "GeminiConfig",
            "id": GEMINI_CONFIG_ID,
            "name": GEMINI_CONFIG_NAME,
            "model_id": "gemini-2.0-flash-lite",
            "agentspec_version": AgentSpecVersionEnum.v26_2_0.value,
        }
    )

    with pytest.raises(ValidationError, match="auth"):
        AgentSpecDeserializer().from_json(serialized_llm)


@pytest.mark.parametrize(
    "model_id",
    [
        "gemini/gemini-2.5-flash",
        "vertex_ai/gemini-2.0-flash-lite",
    ],
)
def test_gemini_config_preserves_prefixed_model_id(model_id: str) -> None:
    llm_config = GeminiConfig(
        id=GEMINI_CONFIG_ID,
        name=GEMINI_CONFIG_NAME,
        model_id=model_id,
        auth=GeminiAIStudioAuthConfig(
            id=GEMINI_AISTUDIO_AUTH_ID,
            name=GEMINI_AISTUDIO_AUTH_NAME,
        ),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    serialized_llm_as_dict = json.loads(serialized_llm)
    _assert_serialized_geminiconfig_fields(serialized_llm_as_dict, model_id=model_id)
    assert serialized_llm_as_dict["auth"]["component_type"] == "GeminiAIStudioAuthConfig"

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert llm_config.model_id == model_id
    assert deserialized_llm.model_id == model_id


def test_serializing_gemini_config_with_unsupported_version_raises_error() -> None:
    llm_config = GeminiConfig(
        name=GEMINI_CONFIG_NAME,
        model_id="gemini-2.5-flash",
        auth=GeminiAIStudioAuthConfig(name=GEMINI_AISTUDIO_AUTH_NAME),
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(
            llm_config,
            agentspec_version=AgentSpecVersionEnum.v26_1_0,
        )
