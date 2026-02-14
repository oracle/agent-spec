# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import json
from pathlib import Path
from typing import Any, Type

import jsonschema
import pytest
import yaml
from jsonschema import validate
from pydantic import Field

from pyagentspec._component_registry import BUILTIN_CLASS_MAP
from pyagentspec.agent import Agent
from pyagentspec.component import Component
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import LlmNode
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.versioning import AgentSpecVersionEnum

from .conftest import read_agentspec_config_file


def test_llmconfig_schema_contains_all_concrete_llmconfig_types() -> None:
    schema = LlmConfig.model_json_schema()
    assert "anyOf" in schema
    llm_config_subtypes = [
        component_type
        for component_type in BUILTIN_CLASS_MAP.values()
        if issubclass(component_type, LlmConfig) and component_type is not LlmConfig
    ]
    for component_type in llm_config_subtypes:
        assert component_type.__name__ in schema["$defs"]
    assert AgentSpecVersionEnum.__name__ in schema["$defs"]
    # +1 because the schema includes ComponentReferenceWithNestedReferences
    assert len(schema["anyOf"]) == len(llm_config_subtypes) + 1


def test_llmnode_schema_contains_all_concrete_llmconfig_types() -> None:
    schema = LlmNode.model_json_schema()
    # because all concrete components can be either serialized as a reference or as their properties
    # directly, the specifications is of type `anyOf` containing these two options.
    assert "anyOf" in schema
    assert set(referenced_type["$ref"] for referenced_type in schema["anyOf"]) == {
        "#/$defs/VersionedComponentReferenceWithNestedReferences",
        "#/$defs/VersionedBaseLlmNode",
    }
    llm_config_subtypes = [
        component_type
        for component_type in BUILTIN_CLASS_MAP.values()
        if issubclass(component_type, LlmConfig) and component_type is not LlmConfig
    ]
    for component_type in llm_config_subtypes:
        assert component_type.__name__ in schema["$defs"]


def test_flow_schema_contains_all_concrete_node_types() -> None:
    schema = Flow.model_json_schema(mode="serialization")
    node_types = [
        component_type
        for component_type in BUILTIN_CLASS_MAP.values()
        if issubclass(component_type, Node)
    ]
    for component_type in node_types:
        assert component_type.__name__ in schema["$defs"]


def test_agent_schema_contains_all_concrete_llm_types() -> None:
    schema = Agent.model_json_schema(mode="serialization")
    node_types = [
        component_type
        for component_type in BUILTIN_CLASS_MAP.values()
        if issubclass(component_type, LlmConfig)
    ]
    for component_type in node_types:
        assert component_type.__name__ in schema["$defs"]


@pytest.mark.parametrize("by_alias", [True, False])
def test_schema_by_alias(by_alias: bool) -> None:
    class CustomAliasNode(Node):
        foo: str = Field(alias="foo_alias")

    schema = CustomAliasNode.model_json_schema(mode="serialization", by_alias=by_alias)
    alias_node_def = schema["$defs"][f"Base{CustomAliasNode.__name__}"]

    if by_alias:
        assert "foo" not in alias_node_def["properties"]
        assert "foo_alias" in alias_node_def["properties"]
    else:
        assert "foo" in alias_node_def["properties"]
        assert "foo_alias" not in alias_node_def["properties"]


EXAMPLE_LLM_CONFIG = VllmConfig(
    name="some name",
    model_id="some model id",
    url="some url",
)

EXAMPLE_LLM_NODE = LlmNode(
    name="some name",
    prompt_template="some_prompt",
    llm_config=EXAMPLE_LLM_CONFIG,
)

EXAMPLE_AGENT = Agent(
    name="Funny agent",
    llm_config=EXAMPLE_LLM_CONFIG,
    system_prompt="No matter what the user asks, don't reply but make a joke instead",
)


@pytest.mark.parametrize(
    "component",
    [
        EXAMPLE_LLM_CONFIG,
        EXAMPLE_LLM_NODE,
        EXAMPLE_AGENT,
    ],
)
def test_generated_schema_correctly_validates_components_serializations(
    component: Component,
) -> None:
    serialized_component = AgentSpecSerializer().to_yaml(component)
    component_schema = component.model_json_schema(mode="serialization")
    validate(yaml.safe_load(serialized_component), component_schema)


@pytest.mark.parametrize(
    "file_path, component_type",
    [
        ("flow_with_multiple_levels_of_references.yaml", Flow),
        ("example_serialized_agent_with_tools.yaml", Agent),
        ("example_serialized_agent_with_tools_and_toolboxes_25_4_2.yaml", Agent),
        ("example_serialized_agent_with_tools_and_toolboxes_26_2_0.yaml", Agent),
        ("example_serialized_flow.yaml", Flow),
        ("example_serialized_flow_executing_agent.yaml", Flow),
        ("example_serialized_flow_with_branching_node.yaml", Flow),
        ("example_serialized_flow_with_properties.yaml", Flow),
        ("example_serialized_llm_node.yaml", LlmNode),
        ("serialized_flow_with_inlined_components.yaml", Flow),
        ("example_serialized_llm_node_without_agentspec_version.yaml", LlmNode),
        ("example_serialized_llm_node_as_nested_reference.yaml", LlmNode),
        ("example_serialized_llm_node_as_versioned_nested_reference.yaml", LlmNode),
    ],
)
def test_generated_schema_correctly_validates_all_valid_serializations(
    file_path: str, component_type: Type[Component]
) -> None:
    serialized_component = read_agentspec_config_file(file_path)
    component_schema = component_type.model_json_schema(only_core_components=True)
    validate(yaml.safe_load(serialized_component), component_schema)


@pytest.mark.parametrize(
    "file_path, component_type",
    [
        ("flow_with_multiple_levels_of_references.yaml", LlmNode),
        ("example_serialized_agent_with_tools.yaml", Flow),
        ("example_serialized_flow.yaml", Agent),
        ("example_serialized_flow_executing_agent.yaml", Agent),
        ("example_serialized_flow_with_branching_node.yaml", Node),
        ("example_serialized_flow_with_properties.yaml", Agent),
        ("example_serialized_llm_node.yaml", Flow),
        ("serialized_flow_with_inlined_components.yaml", LlmConfig),
        ("invalid/example_serialized_llm_node_with_misplaced_agentspec_version.yaml", LlmNode),
        (
            "invalid/example_serialized_llm_node_as_nested_reference_with_incorrect_version.yaml",
            LlmNode,
        ),
    ],
)
def test_generated_schema_correctly_raise_when_type_does_not_match_or_config_is_invalid(
    file_path: str, component_type: Type[Component]
) -> None:
    serialized_component = read_agentspec_config_file(file_path)
    component_schema = component_type.model_json_schema()
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate(yaml.safe_load(serialized_component), component_schema)


def test_json_schema_generation_works_on_custom_components() -> None:

    class CustomComponent(Component):
        custom_attribute: str = "custom_value"

    custom_component_json_schema = CustomComponent.model_json_schema()
    assert "properties" in custom_component_json_schema
    assert "id" in custom_component_json_schema["properties"]
    assert "custom_attribute" in custom_component_json_schema["properties"]
    assert "nonexisting_attribute" not in custom_component_json_schema["properties"]


def test_json_schema_generation_applies_referencing_on_custom_components() -> None:

    class CustomComponent(Component):
        custom_attribute: str = "custom_value"

    class AnotherCustomComponent(Component):
        another_custom_attribute: str = "another_custom_value"

    component_json_schema = Component.model_json_schema()
    assert "$defs" in component_json_schema
    for component_name in ["CustomComponent", "AnotherCustomComponent"]:
        assert component_name in component_json_schema["$defs"]
        assert "anyOf" in component_json_schema["$defs"][component_name]
        assert {"$ref": "#/$defs/ComponentReference"} in component_json_schema["$defs"][
            component_name
        ]["anyOf"]
        assert {"$ref": f"#/$defs/Base{component_name}"} in component_json_schema["$defs"][
            component_name
        ]["anyOf"]


def test_is_abstract_flag_is_set_correctly() -> None:
    component_json_schema = Component.model_json_schema()
    assert "$defs" in component_json_schema
    for component_type_name, component_type_class in BUILTIN_CLASS_MAP.items():
        if isinstance(component_type_class, Component):
            assert "x-abstract-component" in component_json_schema["$defs"][component_type_name]
            assert (
                component_json_schema["$defs"][component_type_name]["x-abstract-component"]
                == component_type_class._is_abstract
            )


def test_inheritance_is_correctly_applied() -> None:

    class ParentComponent(Component):
        pass

    class ChildComponentA(ParentComponent):
        pass

    class ChildComponentB(ParentComponent):
        pass

    component_json_schema = Component.model_json_schema()
    assert "$defs" in component_json_schema
    assert "ParentComponent" in component_json_schema["$defs"]
    assert "BaseParentComponent" in component_json_schema["$defs"]
    assert "BaseChildComponentA" in component_json_schema["$defs"]
    assert "BaseChildComponentB" in component_json_schema["$defs"]
    assert "anyOf" in component_json_schema["$defs"]["BaseParentComponent"]
    assert len(component_json_schema["$defs"]["BaseParentComponent"]["anyOf"]) == 3
    assert {"$ref": "#/$defs/ChildComponentA"} in component_json_schema["$defs"][
        "BaseParentComponent"
    ]["anyOf"]
    assert {"$ref": "#/$defs/ChildComponentB"} in component_json_schema["$defs"][
        "BaseParentComponent"
    ]["anyOf"]


def test_component_schema_generation_works() -> None:
    component_json_schema = Component.model_json_schema(only_core_components=False)
    assert "$defs" in component_json_schema


def test_component_schema_corresponds_to_agentspec_schema_in_docs() -> None:
    # If this test fails because the Agent Spec json schema was updated, please update the
    # reference json schema displayed in the docs at the path specified below. It should be updated
    # with the json dump of `Component.model_json_schema(only_core_components=True)`
    agentspec_version = AgentSpecVersionEnum.current_version.value.replace(".", "_")
    agentspec_version_file = f"agentspec_json_spec_{agentspec_version}.json"
    component_json_schema = Component.model_json_schema(only_core_components=True)
    docs_dir = Path(__file__).parents[2] / "docs" / "pyagentspec" / "source"
    agentspec_spec_json_path = docs_dir / "agentspec" / "json_spec" / agentspec_version_file
    with open(agentspec_spec_json_path, "r") as spec_file:
        docs_component_schema = json.load(spec_file)

    def get_ordering_key(x: Any) -> Any:
        return x.get("title", x.get("$ref", "")) if isinstance(x, dict) else x

    def normalize(obj):
        """Recursively normalize lists by sorting their contents, and process nested dicts/lists."""
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return list(sorted((normalize(v) for v in obj), key=get_ordering_key))
        else:
            return obj

    normalized_component_json_schema = normalize(component_json_schema)
    ## this schema need to be put in the doc
    ## uncomment the line below and copy it in the current json spec
    # agentspec_spec_json_path.write_text(json.dumps(normalized_component_json_schema, indent=2))

    assert normalized_component_json_schema == docs_component_schema
