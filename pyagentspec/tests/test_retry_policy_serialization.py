# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest
from pydantic import ValidationError

from pyagentspec import Agent, AgentSpecDeserializer, AgentSpecSerializer, RetryPolicy
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import ApiNode, EndNode, LlmNode, StartNode
from pyagentspec.llms import OciGenAiConfig
from pyagentspec.llms.ociclientconfig import OciClientConfigWithInstancePrincipal
from pyagentspec.mcp.clienttransport import SSETransport
from pyagentspec.property import Property
from pyagentspec.tools import RemoteTool
from pyagentspec.versioning import AgentSpecVersionEnum


@pytest.fixture
def retry_policy() -> RetryPolicy:
    """Create a non-default retry policy used in versioning tests."""

    return RetryPolicy(max_attempts=3, request_timeout=0.5, initial_retry_delay=1)


@pytest.fixture
def llm_config_with_retry_policy(retry_policy: RetryPolicy) -> OciGenAiConfig:
    """Create an OCI GenAI config with retry policy enabled."""

    return OciGenAiConfig(
        name="oci",
        model_id="meta.llama-3.3-70b-instruct",
        compartment_id="ocid1.compartment.oc1..exampleuniqueID",
        client_config=OciClientConfigWithInstancePrincipal(
            name="oci-client",
            service_endpoint="https://example.invalid",
        ),
        retry_policy=retry_policy,
    )


@pytest.fixture
def api_node_with_retry_policy(retry_policy: RetryPolicy) -> ApiNode:
    """Create an ApiNode with retry policy enabled."""

    return ApiNode(
        name="api",
        url="https://example.invalid",
        http_method="GET",
        retry_policy=retry_policy,
    )


@pytest.fixture
def remote_tool_with_retry_policy(retry_policy: RetryPolicy) -> RemoteTool:
    """Create a RemoteTool with retry policy enabled."""

    return RemoteTool(
        name="rt",
        description="d",
        url="https://example.invalid",
        http_method="GET",
        retry_policy=retry_policy,
    )


@pytest.fixture
def remote_transport_with_retry_policy(retry_policy: RetryPolicy) -> SSETransport:
    """Create a remote MCP transport with retry policy enabled."""

    return SSETransport(
        name="sse-transport",
        url="https://example.invalid/sse",
        retry_policy=retry_policy,
    )


def test_retry_policy_serialization_roundtrip_on_llm_config(
    llm_config_with_retry_policy: OciGenAiConfig,
) -> None:
    start = StartNode(
        name="start",
        inputs=[Property(json_schema={"title": "name", "type": "string"})],
    )
    node = LlmNode(
        name="node",
        llm_config=llm_config_with_retry_policy,
        prompt_template="Hi {{name}}!",
        inputs=[Property(json_schema={"title": "name", "type": "string"})],
    )
    end = EndNode(name="end")
    flow = Flow(
        name="f",
        start_node=start,
        nodes=[start, node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start, to_node=node),
            ControlFlowEdge(name="node_to_end", from_node=node, to_node=end),
        ],
    )

    dumped = AgentSpecSerializer().to_dict(flow)
    loaded = AgentSpecDeserializer().from_dict(dumped)

    assert AgentSpecSerializer().to_dict(loaded) == dumped


def test_retry_policy_serialization_roundtrip_on_agent(
    llm_config_with_retry_policy: OciGenAiConfig,
) -> None:
    agent = Agent(name="a", system_prompt="hi", llm_config=llm_config_with_retry_policy)

    dumped = AgentSpecSerializer().to_dict(agent)
    loaded = AgentSpecDeserializer().from_dict(dumped)

    assert AgentSpecSerializer().to_dict(loaded) == dumped


def test_retry_policy_serialization_roundtrip_on_apinode_and_remotetool(
    api_node_with_retry_policy: ApiNode,
    remote_tool_with_retry_policy: RemoteTool,
    remote_transport_with_retry_policy: SSETransport,
) -> None:
    dumped_api = AgentSpecSerializer().to_dict(api_node_with_retry_policy)
    loaded_api = AgentSpecDeserializer().from_dict(dumped_api)
    assert AgentSpecSerializer().to_dict(loaded_api) == dumped_api

    dumped_tool = AgentSpecSerializer().to_dict(remote_tool_with_retry_policy)
    loaded_tool = AgentSpecDeserializer().from_dict(dumped_tool)
    assert AgentSpecSerializer().to_dict(loaded_tool) == dumped_tool

    dumped_transport = AgentSpecSerializer().to_dict(remote_transport_with_retry_policy)
    loaded_transport = AgentSpecDeserializer().from_dict(dumped_transport)
    assert AgentSpecSerializer().to_dict(loaded_transport) == dumped_transport


def test_retry_policy_present_in_current_version_serialization(
    llm_config_with_retry_policy: OciGenAiConfig,
) -> None:
    agent_with_retry = Agent(
        name="a",
        system_prompt="hi",
        llm_config=llm_config_with_retry_policy,
    )

    dumped = AgentSpecSerializer().to_dict(
        agent_with_retry, agentspec_version=AgentSpecVersionEnum.current_version
    )

    dumped_llm_cfg = dumped["llm_config"]
    assert "retry_policy" in dumped_llm_cfg


@pytest.mark.parametrize(
    "component_fixture_name",
    [
        "llm_config_with_retry_policy",
        "api_node_with_retry_policy",
        "remote_tool_with_retry_policy",
        "remote_transport_with_retry_policy",
    ],
)
def test_retry_policy_defaults_to_v26_2_0(component_fixture_name: str, request) -> None:
    component = request.getfixturevalue(component_fixture_name)

    dumped = AgentSpecSerializer().to_dict(component)

    assert dumped["agentspec_version"] == AgentSpecVersionEnum.v26_2_0.value


@pytest.mark.parametrize(
    "component_fixture_name",
    [
        "llm_config_with_retry_policy",
        "api_node_with_retry_policy",
        "remote_tool_with_retry_policy",
        "remote_transport_with_retry_policy",
    ],
)
def test_retry_policy_serialization_with_unsupported_version_raises(
    component_fixture_name: str, request
) -> None:
    component = request.getfixturevalue(component_fixture_name)

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecSerializer().to_dict(component, agentspec_version=AgentSpecVersionEnum.v26_1_0)


@pytest.mark.parametrize(
    "component_fixture_name",
    [
        "llm_config_with_retry_policy",
        "api_node_with_retry_policy",
        "remote_tool_with_retry_policy",
        "remote_transport_with_retry_policy",
    ],
)
def test_retry_policy_deserialization_with_unsupported_version_raises(
    component_fixture_name: str, request
) -> None:
    component = request.getfixturevalue(component_fixture_name)
    dumped = AgentSpecSerializer().to_dict(component)

    assert dumped["agentspec_version"] == AgentSpecVersionEnum.v26_2_0.value
    dumped["agentspec_version"] = AgentSpecVersionEnum.v26_1_0.value

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        AgentSpecDeserializer().from_dict(dumped)


def test_retry_policy_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RetryPolicy(max_attmpts=7)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_attempts", -1),
        ("request_timeout", 0.0),
        ("request_timeout", -1.0),
        ("initial_retry_delay", -0.1),
        ("max_retry_delay", -0.1),
        ("backoff_factor", 0.0),
        ("backoff_factor", -1.0),
    ],
)
def test_retry_policy_rejects_invalid_numeric_values(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        RetryPolicy(**{field_name: value})


def test_retry_policy_rejects_max_retry_delay_lower_than_initial_delay() -> None:
    with pytest.raises(
        ValidationError,
        match="`max_retry_delay` must be greater than or equal to `initial_retry_delay`",
    ):
        RetryPolicy(initial_retry_delay=2.0, max_retry_delay=1.0)


def test_retry_policy_json_schema_enforces_closed_model_and_bounds() -> None:
    schema = RetryPolicy.model_json_schema()
    request_timeout_schema = schema["properties"]["request_timeout"]
    request_timeout_number_branch = next(
        entry for entry in request_timeout_schema["anyOf"] if entry.get("type") == "number"
    )

    assert schema["additionalProperties"] is False
    assert schema["properties"]["max_attempts"]["minimum"] == 0
    assert request_timeout_number_branch["exclusiveMinimum"] == 0
    assert schema["properties"]["initial_retry_delay"]["minimum"] == 0
    assert schema["properties"]["max_retry_delay"]["minimum"] == 0
    assert schema["properties"]["backoff_factor"]["exclusiveMinimum"] == 0
