# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json

import pytest
from pydantic import ValidationError

from pyagentspec.llms import GeminiAiStudioAuthConfig, GeminiConfig, GeminiVertexAiAuthConfig
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum


def _assert_serialized_geminiconfig_json(
    serialized_llm: str,
    *,
    model_id: str,
    auth: dict[str, object],
) -> None:
    assert json.loads(serialized_llm) == {
        "component_type": "GeminiConfig",
        "id": "gemini-config-id",
        "name": "gemini",
        "description": None,
        "metadata": {},
        "default_generation_parameters": None,
        "model_id": model_id,
        "auth": auth,
        "agentspec_version": AgentSpecVersionEnum.v26_2_0.value,
    }


def test_geminiconfig_empty_aistudio_auth_round_trips_inline_without_registry() -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id="gemini-2.5-flash",
        auth=GeminiAiStudioAuthConfig(),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)

    assert '"$component_ref"' not in serialized_llm
    _assert_serialized_geminiconfig_json(
        serialized_llm,
        model_id="gemini-2.5-flash",
        auth={"type": "aistudio", "api_key": None},
    )

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, GeminiAiStudioAuthConfig)
    assert deserialized_llm.min_agentspec_version == AgentSpecVersionEnum.v26_2_0


def test_geminiconfig_requires_auth() -> None:
    with pytest.raises(ValidationError, match="auth"):
        GeminiConfig(name="gemini", model_id="gemini-2.5-flash")


def test_geminiconfig_aistudio_auth_is_exported_as_sensitive_reference() -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id="gemini-2.5-flash",
        auth=GeminiAiStudioAuthConfig(api_key="THIS_IS_SECRET"),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)

    assert "THIS_IS_SECRET" not in serialized_llm
    assert '"$component_ref":"gemini-config-id.auth"' in serialized_llm.replace(" ", "")

    with pytest.raises(
        ValueError,
        match=r"gemini-config-id\.auth",
    ):
        AgentSpecDeserializer().from_json(serialized_llm)

    deserialized_llm = AgentSpecDeserializer().from_json(
        serialized_llm,
        components_registry={
            "gemini-config-id.auth": {
                "type": "aistudio",
                "api_key": "THIS_IS_SECRET",
            }
        },
    )
    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, GeminiAiStudioAuthConfig)


def test_geminiconfig_vertex_auth_is_exported_as_sensitive_reference() -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id="gemini-2.0-flash-lite",
        auth=GeminiVertexAiAuthConfig(
            project_id="project-id",
            location="global",
            credentials={
                "type": "service_account",
                "client_email": "agent@example.com",
                "private_key": "line1\\nline2",
            },
        ),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)

    assert "service_account" not in serialized_llm
    assert '"$component_ref":"gemini-config-id.auth"' in serialized_llm.replace(" ", "")

    deserialized_llm = AgentSpecDeserializer().from_json(
        serialized_llm,
        components_registry={
            "gemini-config-id.auth": {
                "type": "vertex_ai",
                "project_id": "project-id",
                "location": "global",
                "credentials": {
                    "type": "service_account",
                    "client_email": "agent@example.com",
                    "private_key": "line1\\nline2",
                },
            }
        },
    )
    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, GeminiVertexAiAuthConfig)


def test_geminiconfig_empty_vertex_auth_round_trips_inline_without_registry() -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id="gemini-2.0-flash-lite",
        auth=GeminiVertexAiAuthConfig(),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)

    assert '"$component_ref"' not in serialized_llm
    _assert_serialized_geminiconfig_json(
        serialized_llm,
        model_id="gemini-2.0-flash-lite",
        auth={
            "type": "vertex_ai",
            "project_id": None,
            "location": "global",
            "credentials": None,
        },
    )

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, GeminiVertexAiAuthConfig)


def test_geminiconfig_vertex_auth_without_credentials_round_trips_inline() -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id="gemini-2.0-flash-lite",
        auth=GeminiVertexAiAuthConfig(
            project_id="project-id",
            location="us-central1",
        ),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)

    assert '"$component_ref"' not in serialized_llm
    _assert_serialized_geminiconfig_json(
        serialized_llm,
        model_id="gemini-2.0-flash-lite",
        auth={
            "type": "vertex_ai",
            "project_id": "project-id",
            "location": "us-central1",
            "credentials": None,
        },
    )

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert deserialized_llm == llm_config
    assert isinstance(deserialized_llm.auth, GeminiVertexAiAuthConfig)
    assert deserialized_llm.auth.project_id == "project-id"
    assert deserialized_llm.auth.location == "us-central1"


def test_geminiconfig_inline_vertex_auth_can_be_deserialized() -> None:
    serialized_llm = """{
      "component_type": "GeminiConfig",
      "id": "gemini-config-id",
      "name": "gemini",
      "model_id": "gemini-2.0-flash-lite",
      "auth": {"type": "vertex_ai"},
      "agentspec_version": "26.2.0"
    }"""

    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert isinstance(deserialized_llm, GeminiConfig)
    assert isinstance(deserialized_llm.auth, GeminiVertexAiAuthConfig)
    assert deserialized_llm.auth == GeminiVertexAiAuthConfig()


def test_geminiconfig_missing_auth_cannot_be_deserialized() -> None:
    serialized_llm = """{
      "component_type": "GeminiConfig",
      "id": "gemini-config-id",
      "name": "gemini",
      "model_id": "gemini-2.0-flash-lite",
      "agentspec_version": "26.2.0"
    }"""

    with pytest.raises(ValidationError, match="auth"):
        AgentSpecDeserializer().from_json(serialized_llm)


@pytest.mark.parametrize(
    "model_id",
    [
        "gemini/gemini-2.5-flash",
        "vertex_ai/gemini-2.0-flash-lite",
    ],
)
def test_geminiconfig_preserves_prefixed_model_id(model_id: str) -> None:
    llm_config = GeminiConfig(
        id="gemini-config-id",
        name="gemini",
        model_id=model_id,
        auth=GeminiAiStudioAuthConfig(),
    )

    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    _assert_serialized_geminiconfig_json(
        serialized_llm,
        model_id=model_id,
        auth={"type": "aistudio", "api_key": None},
    )
    deserialized_llm = AgentSpecDeserializer().from_json(serialized_llm)

    assert llm_config.model_id == model_id
    assert deserialized_llm.model_id == model_id


def test_geminiconfig_cannot_be_exported_to_pre_26_2_version() -> None:
    llm_config = GeminiConfig(
        name="gemini",
        model_id="gemini-2.5-flash",
        auth=GeminiAiStudioAuthConfig(),
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(
            llm_config,
            agentspec_version=AgentSpecVersionEnum.v26_1_0,
        )
