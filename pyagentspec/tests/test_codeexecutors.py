# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (https://oss.oracle.com/licenses/upl), at your option.

import json
from typing import Callable

import pytest
from pydantic import ValidationError

from pyagentspec import (
    AgentSpecDeserializer,
    AgentSpecSerializer,
    CodeExecutor,
    EndpointCodeExecutor,
    LocalContainerCodeExecutor,
    RetryPolicy,
    SubProcessCodeExecutor,
)
from pyagentspec._component_registry import BUILTIN_CLASS_MAP
from pyagentspec.versioning import AgentSpecVersionEnum


def test_code_executor_defaults() -> None:
    executor = SubProcessCodeExecutor(name="subprocess")

    assert executor.timeout_seconds == 30.0
    assert executor.max_code_chars == 50_000
    assert executor.component_type == "SubProcessCodeExecutor"
    assert executor.min_agentspec_version == AgentSpecVersionEnum.v26_2_0


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("max_code_chars", 0),
        ("max_code_chars", -1),
    ],
)
def test_code_executor_rejects_non_positive_limits(field_name: str, invalid_value: int) -> None:
    with pytest.raises(ValidationError):
        SubProcessCodeExecutor(name="subprocess", **{field_name: invalid_value})


@pytest.mark.parametrize(
    "executor_class",
    [LocalContainerCodeExecutor, EndpointCodeExecutor],
)
def test_code_executor_required_backend_fields(executor_class: type[CodeExecutor]) -> None:
    with pytest.raises(ValidationError):
        executor_class(name="executor")


def test_local_container_executor_and_endpoint_executor_configuration() -> None:
    container = LocalContainerCodeExecutor(name="container", image="python:3.12")
    endpoint = EndpointCodeExecutor(
        name="endpoint",
        url="https://executor.example.invalid/run",
        headers={"X-Request-Id": "request-id"},
        sensitive_headers={"Authorization": "Bearer secret"},
    )

    assert container.image == "python:3.12"
    assert endpoint.url == "https://executor.example.invalid/run"
    assert endpoint.headers == {"X-Request-Id": "request-id"}
    assert endpoint.sensitive_headers == {"Authorization": "Bearer secret"}


def test_endpoint_sensitive_headers_are_excluded_by_default_and_exported_on_opt_in() -> None:
    endpoint = EndpointCodeExecutor(
        name="endpoint",
        url="https://executor.example.invalid/run",
        headers={"X-Request-Id": "request-id"},
        sensitive_headers={"Authorization": "Bearer secret"},
    )

    serialized = AgentSpecSerializer().to_dict(endpoint)
    assert serialized["headers"] == {"X-Request-Id": "request-id"}
    # Default serialization replaces non-empty sensitive values with references.
    assert serialized["sensitive_headers"] == {"$component_ref": f"{endpoint.id}.sensitive_headers"}

    # Sensitive values require an explicit opt-in before they are serialized.
    with pytest.warns(UserWarning):
        serialized_with_sensitive_headers = AgentSpecSerializer().to_dict(
            endpoint, include_sensitive_fields=True
        )
    assert serialized_with_sensitive_headers["sensitive_headers"] == {
        "Authorization": "Bearer secret"
    }


def test_endpoint_retry_policy_roundtrip() -> None:
    endpoint = EndpointCodeExecutor(
        name="endpoint",
        url="https://executor.example.invalid/run",
        retry_policy=RetryPolicy(max_attempts=3, request_timeout=0.5),
    )

    serialized = AgentSpecSerializer().to_dict(endpoint)
    deserialized = AgentSpecDeserializer().from_dict(serialized)

    assert isinstance(deserialized, EndpointCodeExecutor)
    assert deserialized.retry_policy == endpoint.retry_policy
    assert AgentSpecSerializer().to_dict(deserialized) == serialized


def test_code_executor_is_abstract() -> None:
    with pytest.raises(TypeError, match="meant to be abstract"):
        CodeExecutor(name="executor")


@pytest.mark.parametrize(
    "executor_class",
    [
        CodeExecutor,
        SubProcessCodeExecutor,
        LocalContainerCodeExecutor,
        EndpointCodeExecutor,
    ],
)
def test_code_executors_are_builtin_components(executor_class: type[CodeExecutor]) -> None:
    assert BUILTIN_CLASS_MAP[executor_class.__name__] is executor_class


@pytest.mark.parametrize(
    ("executor", "serializer", "deserializer"),
    [
        (
            SubProcessCodeExecutor(name="subprocess"),
            AgentSpecSerializer().to_json,
            AgentSpecDeserializer().from_json,
        ),
        (
            LocalContainerCodeExecutor(name="container", image="python:3.12"),
            AgentSpecSerializer().to_yaml,
            AgentSpecDeserializer().from_yaml,
        ),
        (
            EndpointCodeExecutor(
                name="endpoint",
                url="https://executor.example.invalid/run",
                headers={"X-Request-Id": "request-id"},
                retry_policy=RetryPolicy(max_attempts=3),
            ),
            AgentSpecSerializer().to_json,
            AgentSpecDeserializer().from_json,
        ),
    ],
    ids=["subprocess-json", "container-yaml", "endpoint-json"],
)
def test_code_executor_json_and_yaml_roundtrips(
    executor: CodeExecutor,
    serializer: Callable[[CodeExecutor], str],
    deserializer: Callable[[str], CodeExecutor],
) -> None:
    serialized = serializer(executor)
    deserialized = deserializer(serialized)

    assert deserialized == executor
    if serialized.lstrip().startswith("{"):
        assert json.loads(serialized)["component_type"] == executor.component_type
    else:
        assert "component_type: " + executor.component_type in serialized


def test_code_executor_rejects_serialization_before_v26_2_0() -> None:
    executor = SubProcessCodeExecutor(name="subprocess")

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(executor, agentspec_version=AgentSpecVersionEnum.v26_1_2)


def test_code_executor_rejects_deserialization_before_v26_2_0() -> None:
    executor = SubProcessCodeExecutor(name="subprocess")
    serialized = AgentSpecSerializer().to_dict(executor)
    serialized["agentspec_version"] = AgentSpecVersionEnum.v26_1_2.value

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_dict(serialized)
