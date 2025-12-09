# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest
from pydantic_core._pydantic_core import ValidationError

from pyagentspec import Agent, AgentSpecDeserializer, AgentSpecSerializer, Component
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, ApiNode, EndNode, StartNode
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.llms.ociclientconfig import (
    OciClientConfigWithApiKey,
    OciClientConfigWithSecurityToken,
)
from pyagentspec.mcp import MCPToolBox
from pyagentspec.mcp.clienttransport import (
    SSEmTLSTransport,
    SSETransport,
    StreamableHTTPmTLSTransport,
)
from pyagentspec.tools import RemoteTool


# All components used as test case have the string 'abcdexyz' added on a sensitive field.
# This string should be excluded when serializing.
@pytest.mark.parametrize(
    "component",
    [
        OpenAiCompatibleConfig(
            name="openai-compatible-config",
            url="https://api.closedai.com/v2",
            model_id="gpt-7",
            api_key="abcdexyz",
        ),
        OciClientConfigWithSecurityToken(
            name="name",
            auth_file_location="path/to/abcdexyz.json",
            auth_profile="default",
            service_endpoint="https://some.url",
        ),
        OciClientConfigWithApiKey(
            name="name",
            auth_file_location="path/to/abcdexyz.json",
            auth_profile="default",
            service_endpoint="https://some.url",
        ),
        RemoteTool(
            name="name",
            url="https://some.url",
            http_method="GET",
            sensitive_headers={"Authorization": "Bearer abcdexyz"},
        ),
        ApiNode(
            name="name",
            url="https://some.url",
            http_method="GET",
            sensitive_headers={"Authorization": "Bearer abcdexyz"},
        ),
        SSETransport(
            name="name",
            url="https://some.url",
            sensitive_headers={"Authorization": "Bearer abcdexyz"},
        ),
        SSEmTLSTransport(
            name="name",
            url="https://some.url",
            cert_file="path/to/abcdexyz.json",
            key_file="path/to/abcdexyz.json",
            ca_file="path/to/abcdexyz.json",
        ),
        StreamableHTTPmTLSTransport(
            name="name",
            url="https://some.url",
            cert_file="path/to/abcdexyz.json",
            key_file="path/to/abcdexyz.json",
            ca_file="path/to/abcdexyz.json",
        ),
    ],
)
def test_exported_component_does_not_contain_sensitive_field(component: Component) -> None:
    serialized_component = AgentSpecSerializer().to_json(component)
    assert "abcdexyz" not in serialized_component
    assert "$component_ref" in serialized_component


def test_configuration_new_api_key_sensitive_field_and_old_version_25_4_1_cannot_be_loaded():
    serialized_llm = """{
      "component_type": "OpenAiCompatibleConfig",
      "id": "openai-compatible-config-id",
      "name": "openai-compatible-config",
      "url": "https://api.closedai.com/v2",
      "model_id": "gpt-7",
      "api_key": "THIS_SECRET_IS_SAFELY_INLINED",
      "agentspec_version": "25.4.1"
    }"""
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        llm_config = AgentSpecDeserializer().from_json(serialized_llm)


def test_configuration_containing_inlined_sensitive_fields_can_be_loaded():
    serialized_llm = """{
      "component_type": "OpenAiCompatibleConfig",
      "id": "openai-compatible-config-id",
      "name": "openai-compatible-config",
      "url": "https://api.closedai.com/v2",
      "model_id": "gpt-7",
      "api_key": "THIS_SECRET_IS_SAFELY_INLINED",
      "agentspec_version": "25.4.2"
    }"""
    llm_config = AgentSpecDeserializer().from_json(serialized_llm)
    assert isinstance(llm_config, OpenAiCompatibleConfig)
    assert llm_config.api_key == "THIS_SECRET_IS_SAFELY_INLINED"


def test_openaicompatibleconfig_cannot_be_imported_without_the_required_api_key() -> None:
    llm_config = OpenAiCompatibleConfig(
        name="openai-compatible-config",
        id="openai-compatible-config-id",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
        api_key="THIS_IS_SECRET",
    )
    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    with pytest.raises(
        ValueError,
        match=(
            r"The following references to fields or components are missing and should be passed as "
            r"part of the component registry when deserializing: "
            r"\[\'openai-compatible-config-id.api_key\']"
        ),
    ):
        AgentSpecDeserializer().from_json(serialized_llm)


def test_openaicompatibleconfig_without_api_key_can_be_imported_without_api_key() -> None:
    llm_config = OpenAiCompatibleConfig(
        name="openai-compatible-config",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
    )
    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    new_llm_config = AgentSpecDeserializer().from_json(serialized_llm)
    assert new_llm_config == llm_config


def test_openaicompatibleconfig_can_be_imported_with_api_key_in_component_registry() -> None:
    llm_config = OpenAiCompatibleConfig(
        name="openai-compatible-config",
        id="openai-compatible-config-id",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
        api_key="THIS_IS_SECRET",
    )
    serialized_llm = AgentSpecSerializer().to_json(llm_config)
    new_llm_config = AgentSpecDeserializer().from_json(
        serialized_llm,
        components_registry={"openai-compatible-config-id.api_key": "THIS_IS_SECRET"},
    )
    assert new_llm_config == llm_config


@pytest.fixture
def nested_component_with_multiple_sensitive_fields() -> Component:
    mcp_tool_box = MCPToolBox(
        name="mcp-tool-box",
        id="mcp-tool-box-id",
        client_transport=SSETransport(
            name="name",
            id="sse-transport-id",
            url="https://some.url",
            sensitive_headers={"Authorization": "Bearer abcdexyz"},
        ),
    )
    llm_config = OpenAiCompatibleConfig(
        name="openai-compatible-config",
        id="openai-compatible-config-id",
        url="https://api.closedai.com/v2",
        model_id="gpt-7",
        api_key="abcdexyz",
    )
    agent = Agent(
        name="agent",
        llm_config=llm_config,
        toolboxes=[mcp_tool_box],
        system_prompt="be good",
    )
    start_node = StartNode(name="node-1")
    api_node = ApiNode(
        name="node-2",
        id="api-node-id",
        url="https://some.url",
        http_method="GET",
        sensitive_headers={"Authorization": "Bearer abcdexyz"},
    )
    agent_node = AgentNode(
        name="node-3",
        id="node-3-id",
        agent=agent,
    )
    end_node = EndNode(name="node-4")
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, api_node, agent_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=api_node),
            ControlFlowEdge(name="edge", from_node=api_node, to_node=agent_node),
            ControlFlowEdge(name="edge", from_node=agent_node, to_node=end_node),
        ],
    )
    return flow


def test_serialized_nested_components_does_not_contain_sensitive_fields(
    nested_component_with_multiple_sensitive_fields: Component,
) -> None:
    serialized_nested_components = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields
    )
    assert "abcdexyz" not in serialized_nested_components


def test_loading_serialized_nested_components_without_component_registry_raises(
    nested_component_with_multiple_sensitive_fields: Component,
) -> None:
    serialized_nested_components = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields
    )
    with pytest.raises(
        ValueError,
        match=(
            r"api-node-id\.sensitive_headers.*"
            r"openai-compatible-config-id\.api_key.*"
            r"sse-transport-id\.sensitive_headers.*"
        ),
    ):
        AgentSpecDeserializer().from_json(serialized_nested_components)


def test_loading_serialized_nested_components_with_partial_component_registry_raises(
    nested_component_with_multiple_sensitive_fields: Component,
) -> None:
    serialized_nested_components = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields
    )
    with pytest.raises(
        ValueError,
        match=(r"api-node-id\.sensitive_headers.*" r"sse-transport-id\.sensitive_headers.*"),
    ):
        AgentSpecDeserializer().from_json(
            serialized_nested_components,
            components_registry={"openai-compatible-config-id.api_key": "my_api_key"},
        )


def test_loading_serialized_nested_components_with_component_registry_succeeds(
    nested_component_with_multiple_sensitive_fields: Component,
) -> None:
    serialized_nested_components = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields
    )
    new_component = AgentSpecDeserializer().from_json(
        serialized_nested_components,
        components_registry={
            "openai-compatible-config-id.api_key": "abcdexyz",
            "api-node-id.sensitive_headers": {"Authorization": "Bearer abcdexyz"},
            "sse-transport-id.sensitive_headers": {"Authorization": "Bearer abcdexyz"},
        },
    )
    assert new_component.nodes[1].sensitive_headers == {"Authorization": "Bearer abcdexyz"}
    assert new_component.nodes[2].agent.llm_config.api_key == "abcdexyz"
    assert new_component.nodes[2].agent.toolboxes[0].client_transport.sensitive_headers == {
        "Authorization": "Bearer abcdexyz"
    }


def test_sensitive_fields_are_excluded_from_disaggregated_configuration(
    nested_component_with_multiple_sensitive_fields,
):
    main_config, disaggregated_config = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields,
        disaggregated_components=[
            nested_component_with_multiple_sensitive_fields.nodes[0],
            nested_component_with_multiple_sensitive_fields.nodes[1],
            nested_component_with_multiple_sensitive_fields.nodes[2].agent.llm_config,
        ],
        export_disaggregated_components=True,
    )
    assert "abcdexyz" not in main_config
    assert "abcdexyz" not in disaggregated_config


def test_disaggregated_configuration_with_sensitive_fields_can_be_loaded_back(
    nested_component_with_multiple_sensitive_fields,
):
    main_flow_config, disaggregated_agent_config = AgentSpecSerializer().to_json(
        nested_component_with_multiple_sensitive_fields,
        disaggregated_components=[
            nested_component_with_multiple_sensitive_fields.nodes[2].agent,
        ],
        export_disaggregated_components=True,
    )
    deserialized_agent_as_component_registry = AgentSpecDeserializer().from_json(
        disaggregated_agent_config,
        components_registry={
            "openai-compatible-config-id.api_key": "abcdexyz",
            "sse-transport-id.sensitive_headers": {"Authorization": "Bearer abcdexyz"},
        },
        import_only_referenced_components=True,
    )
    deserialized_flow = AgentSpecDeserializer().from_json(
        main_flow_config,
        components_registry={
            **deserialized_agent_as_component_registry,
            "api-node-id.sensitive_headers": {"Authorization": "Bearer abcdexyz"},
        },
    )
    assert deserialized_flow.nodes[1].sensitive_headers == {"Authorization": "Bearer abcdexyz"}
    assert deserialized_flow.nodes[2].agent.llm_config.api_key == "abcdexyz"
    assert deserialized_flow.nodes[2].agent.toolboxes[0].client_transport.sensitive_headers == {
        "Authorization": "Bearer abcdexyz"
    }


def test_partial_configurations_exclude_secrets():
    partial_llm_config = {
        "name": "openai-compatible-config",
        "api_key": "THIS_SECRET_NOT_TO_BE_EXPORTED",
    }
    partial_llm = OpenAiCompatibleConfig.build_from_partial_config(partial_llm_config)
    serialized_partial_llm = AgentSpecSerializer(_allow_partial_model_serialization=True).to_json(
        partial_llm
    )
    assert "THIS_SECRET_NOT_TO_BE_EXPORTED" not in serialized_partial_llm


@pytest.mark.parametrize(
    "component_cls, attributes",
    [
        (
            RemoteTool,
            dict(
                name="name",
                url="https://some.url",
                http_method="GET",
                headers={"Authorization": "Bearer abcdexyz"},
                sensitive_headers={"Authorization": "Bearer abcdexyz"},
            ),
        ),
        (
            ApiNode,
            dict(
                name="name",
                url="https://some.url",
                http_method="GET",
                headers={"Authorization": "Bearer abcdexyz"},
                sensitive_headers={"Authorization": "Bearer abcdexyz"},
            ),
        ),
        (
            SSETransport,
            dict(
                name="name",
                url="https://some.url",
                headers={"Authorization": "Bearer abcdexyz"},
                sensitive_headers={"Authorization": "Bearer abcdexyz"},
            ),
        ),
    ],
)
def test_component_raises_when_headers_and_sensitive_headers_collide(component_cls, attributes):
    with pytest.raises(
        ValidationError,
        match="Found some headers have been specified in both `headers` and `sensitive_headers`:.*Authorization",
    ):
        component_cls(**attributes)
