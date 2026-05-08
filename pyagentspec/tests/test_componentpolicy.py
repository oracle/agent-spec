# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Optional

import pytest

from pyagentspec.component import Component
from pyagentspec.llms import LlmConfig, OpenAiConfig
from pyagentspec.mcp import MCPTool, StdioTransport
from pyagentspec.mcp.clienttransport import ClientTransport
from pyagentspec.serialization import (
    AgentSpecDeserializer,
    AgentSpecSerializer,
    ComponentDeserializationPlugin,
    DeserializationContext,
)
from pyagentspec.serialization.componentpolicy import (
    ComponentLoadPolicy,
    ComponentPolicyInput,
)
from pyagentspec.serialization.pydanticdeserializationplugin import (
    PydanticComponentDeserializationPlugin,
)
from pyagentspec.serialization.pydanticserializationplugin import (
    PydanticComponentSerializationPlugin,
)


class PolicyExtensionComponent(Component):
    value: str = ""


class PolicyExtensionChildComponent(PolicyExtensionComponent):
    child_value: str = ""


class PolicyPluginContainer(Component):
    child: Component


class PolicyBypassDeserializationPlugin(ComponentDeserializationPlugin):
    @property
    def plugin_name(self) -> str:
        return "PolicyBypassDeserializationPlugin"

    @property
    def plugin_version(self) -> str:
        return "0.0.0"

    def supported_component_types(self) -> list[str]:
        return [PolicyPluginContainer.__name__]

    def deserialize(
        self,
        serialized_component: dict[str, Any],
        deserialization_context: DeserializationContext,
    ) -> Component:
        return PolicyPluginContainer(
            name=serialized_component["name"],
            child=StdioTransport(name="plugin_stdio_transport", command="python3"),
        )


def _make_stdio_mcp_tool() -> MCPTool:
    return MCPTool(
        name="stdio_tool",
        client_transport=StdioTransport(
            name="stdio_transport",
            command="python3",
            args=["server.py"],
            env={"EXAMPLE": "1"},
            cwd=".",
        ),
    )


@pytest.mark.parametrize(
    ("allowed_components", "blocked_components", "error_match"),
    [
        ([MCPTool, "StdioTransport"], [], None),
        (
            [MCPTool, "StdioTransport"],
            [StdioTransport],
            "StdioTransport.*in the block list",
        ),
        ([MCPTool], [], "StdioTransport.*not in the allow list"),
        (["StdioTransport"], [], "MCPTool.*not in the allow list"),
    ],
)
def test_component_load_policy_handles_allow_block_combinations_with_mixed_entry_types(
    allowed_components: ComponentPolicyInput,
    blocked_components: ComponentPolicyInput,
    error_match: Optional[str],
) -> None:
    policy = ComponentLoadPolicy(
        allowed_components=allowed_components,
        blocked_components=blocked_components,
    )
    tool = _make_stdio_mcp_tool()

    if error_match is None:
        policy.validate_component_tree(tool)
    else:
        with pytest.raises(ValueError, match=error_match):
            policy.validate_component_tree(tool)


def test_component_load_policy_blocks_child_classes_of_blocked_component_classes() -> None:
    policy = ComponentLoadPolicy(blocked_components=[ClientTransport])

    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        policy.validate_component_tree(_make_stdio_mcp_tool())


def test_component_load_policy_allows_child_classes_of_allowed_component_classes() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=[MCPTool, ClientTransport],
        blocked_components=[],
    )

    policy.validate_component_tree(_make_stdio_mcp_tool())


def test_component_load_policy_blocks_child_classes_of_resolved_component_type_names() -> None:
    policy = ComponentLoadPolicy(blocked_components=["ClientTransport"])

    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        policy.validate_component_tree(_make_stdio_mcp_tool())


def test_component_load_policy_allows_child_classes_of_resolved_component_type_names() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=["MCPTool", "ClientTransport"],
        blocked_components=[],
    )

    policy.validate_component_tree(_make_stdio_mcp_tool())


def test_component_load_policy_uses_more_specific_block_rule() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=[LlmConfig],
        blocked_components=[OpenAiConfig],
    )

    with pytest.raises(ValueError, match="OpenAiConfig.*in the block list"):
        policy.validate_component_tree(OpenAiConfig(name="openai", model_id="gpt-4o"))


def test_component_load_policy_uses_more_specific_allow_rule() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=[OpenAiConfig],
        blocked_components=[LlmConfig],
    )

    policy.validate_component_tree(OpenAiConfig(name="openai", model_id="gpt-4o"))


def test_component_load_policy_exact_type_name_outranks_parent_class_rule() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=["OpenAiConfig"],
        blocked_components=[LlmConfig],
    )

    policy.validate_component_tree(OpenAiConfig(name="openai", model_id="gpt-4o"))


def test_component_load_policy_uses_more_specific_resolved_type_name_rule() -> None:
    policy = ComponentLoadPolicy(
        allowed_components=["OpenAiConfig"],
        blocked_components=["LlmConfig"],
    )

    policy.validate_component_tree(OpenAiConfig(name="openai", model_id="gpt-4o"))


def test_component_load_policy_unresolved_type_names_match_exactly() -> None:
    policy = ComponentLoadPolicy(blocked_components=["UnregisteredComponent"])

    policy.validate_component_tree(OpenAiConfig(name="openai", model_id="gpt-4o"))
    with pytest.raises(ValueError, match="UnregisteredComponent.*in the block list"):
        policy.validate_component_type("UnregisteredComponent")


def test_deserializer_applies_hierarchical_policy_to_loaded_components() -> None:
    serialized_tool = AgentSpecSerializer().to_dict(_make_stdio_mcp_tool())

    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        AgentSpecDeserializer(blocked_components=[ClientTransport]).from_dict(serialized_tool)


def test_component_load_policy_class_entries_work_for_extension_components() -> None:
    component_types_and_models = {
        PolicyExtensionComponent.__name__: PolicyExtensionComponent,
        PolicyExtensionChildComponent.__name__: PolicyExtensionChildComponent,
    }
    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models=component_types_and_models
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models=component_types_and_models
    )
    component = PolicyExtensionChildComponent(
        name="extension_child",
        value="parent-value",
        child_value="child-value",
    )
    serialized_component = AgentSpecSerializer(plugins=[serialization_plugin]).to_dict(component)

    with pytest.raises(ValueError, match="PolicyExtensionChildComponent.*in the block list"):
        AgentSpecDeserializer(
            plugins=[deserialization_plugin],
            blocked_components=[PolicyExtensionComponent],
        ).from_dict(serialized_component)

    loaded_component = AgentSpecDeserializer(
        plugins=[deserialization_plugin],
        allowed_components=[PolicyExtensionComponent],
    ).from_dict(serialized_component)

    assert loaded_component == component


def test_deserializer_validates_component_returned_by_plugin() -> None:
    with pytest.raises(ValueError, match="PolicyPluginContainer.*in the block list"):
        AgentSpecDeserializer(
            plugins=[PolicyBypassDeserializationPlugin()],
            blocked_components=[PolicyPluginContainer],
        ).from_dict(
            {
                "component_type": PolicyPluginContainer.__name__,
                "agentspec_version": "25.4.1",
                "name": "plugin_container",
            }
        )
