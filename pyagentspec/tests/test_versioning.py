# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from typing import Iterable

import pytest
from pydantic import Field

from pyagentspec import __version__
from pyagentspec.component import Component
from pyagentspec.flows.flow import Flow
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.serialization.pydanticdeserializationplugin import (
    PydanticComponentDeserializationPlugin,
)
from pyagentspec.serialization.pydanticserializationplugin import (
    PydanticComponentSerializationPlugin,
)
from pyagentspec.versioning import (
    _LEGACY_AGENTSPEC_VERSIONS,
    _LEGACY_VERSION_FIELD_NAME,
    AGENTSPEC_VERSION_FIELD_NAME,
    AgentSpecVersionEnum,
    _version_lt,
)

from .serialization.conftest import simplest_flow  # noqa: F401


def test_flow_exports_with_agentspec_version(simplest_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    serialized_flow = serializer.to_dict(simplest_flow)

    assert AGENTSPEC_VERSION_FIELD_NAME in serialized_flow
    assert (
        _version_lt(
            serialized_flow[AGENTSPEC_VERSION_FIELD_NAME],
            AgentSpecVersionEnum.current_version.value,
        )
        or serialized_flow[AGENTSPEC_VERSION_FIELD_NAME]
        == AgentSpecVersionEnum.current_version.value
    )


def test_explicit_agentspec_version_export(simplest_flow: Flow) -> None:
    serializer = AgentSpecSerializer()
    agentspec_version = AgentSpecVersionEnum(value=AgentSpecVersionEnum.current_version.value)
    serialized_flow = serializer.to_dict(simplest_flow, agentspec_version=agentspec_version)

    assert AGENTSPEC_VERSION_FIELD_NAME in serialized_flow
    assert serialized_flow[AGENTSPEC_VERSION_FIELD_NAME] == agentspec_version.value
    assert AGENTSPEC_VERSION_FIELD_NAME not in serialized_flow["start_node"]
    for node in serialized_flow["nodes"]:
        assert AGENTSPEC_VERSION_FIELD_NAME not in node


def test_only_top_level_is_versioned_component(simplest_flow: Flow) -> None:
    schema = simplest_flow.model_json_schema()
    assert schema["anyOf"] == [
        {"$ref": "#/$defs/VersionedComponentReferenceWithNestedReferences"},
        {"$ref": "#/$defs/VersionedBaseFlow"},
    ]
    def_keys: Iterable[str] = schema["$defs"]
    for defs in def_keys:
        if defs == "VersionedComponentReferenceWithNestedReferences" or defs == "VersionedBaseFlow":
            continue
        assert not defs.startswith("Versioned")


def test_component_raises_on_invalid_min_max_versions():
    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )

    with pytest.raises(ValueError, match="Invalid min/max versioning for component"):
        _ = MyComponent(name="my_component")


def test_serialization_raises_on_agentspec_version_below_allowed_min() -> None:
    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    component = MyComponent(name="component")
    serializer = AgentSpecSerializer()

    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
    ):
        _ = serializer.to_dict(component, agentspec_version=AgentSpecVersionEnum.v25_3_0)


def test_serialization_raises_on_agentspec_version_above_allowed_max() -> None:
    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )

    component = MyComponent(name="component")

    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyComponent.__name__: MyComponent}
    )
    serializer = AgentSpecSerializer(plugins=[serialization_plugin])

    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the maximum allowed version is.*"
    ):
        _ = serializer.to_dict(component, agentspec_version=AgentSpecVersionEnum.current_version)


def test_deserialization_properly_sets_min_agentspec_version_of_exported_component() -> None:
    class MySubComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        value: MySubComponent

    sub_component = MySubComponent(name="sub_component")
    component = MyComponent(name="component", value=sub_component)

    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={
            MyComponent.__name__: MyComponent,
            MySubComponent.__name__: MySubComponent,
        }
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={
            MyComponent.__name__: MyComponent,
            MySubComponent.__name__: MySubComponent,
        }
    )
    SELECTED_EXPORT_VERSION = AgentSpecVersionEnum.v25_3_0
    obj_as_dict = AgentSpecSerializer(plugins=[serialization_plugin]).to_dict(
        component, agentspec_version=SELECTED_EXPORT_VERSION
    )

    deserialized_component = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_dict(
        obj_as_dict
    )

    assert isinstance(deserialized_component, MyComponent)
    assert deserialized_component.min_agentspec_version == SELECTED_EXPORT_VERSION
    assert deserialized_component.value.min_agentspec_version == SELECTED_EXPORT_VERSION


def test_serialization_raises_on_incompatible_components_minmax_versions() -> None:
    class MySubComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        value: MySubComponent

    sub_component = MySubComponent(name="sub_component")
    component = MyComponent(name="component", value=sub_component)

    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={
            MyComponent.__name__: MyComponent,
            MySubComponent.__name__: MySubComponent,
        }
    )
    with pytest.raises(
        ValueError,
        match="Incompatible agentspec_versions: min agentspec_version.*is greater than max agentspec_version",
    ):
        _ = AgentSpecSerializer(plugins=[serialization_plugin]).to_json(component)


def test_min_version_is_max_of_min_subcomponents() -> None:
    # Parent's min version is max among own and subcomponents
    # 1. sub component sets lower bound
    class MySubComponent1(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    class MyComponent1(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        value: MySubComponent1

    sub_component1 = MySubComponent1(name="sub_component")
    component1 = MyComponent1(name="component", value=sub_component1)
    min_version, min_component = component1._get_min_agentspec_version_and_component()

    assert min_version == sub_component1.min_agentspec_version
    assert min_component is sub_component1  # component lower bounding the version

    # 2. component sets lower bound
    class MySubComponent2(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    class MyComponent2(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        value: MySubComponent2

    sub_component2 = MySubComponent2(name="sub_component")
    component2 = MyComponent2(name="component", value=sub_component2)
    min_version, min_component = component2._get_min_agentspec_version_and_component()

    assert min_version == component2.min_agentspec_version
    assert min_component is component2  # component lower bounding the version


def test_max_version_is_min_of_max_subcomponents() -> None:
    # Parent's max version is min among own and subcomponents
    # 1. sub component sets upper bound
    class MySubComponent1(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_1, exclude=True
        )

    class MyComponent1(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        value: MySubComponent1

    sub_component1 = MySubComponent1(name="sub_component")
    component1 = MyComponent1(name="component", value=sub_component1)
    max_version, max_component = component1._get_max_agentspec_version_and_component()

    assert max_version == sub_component1.max_agentspec_version
    assert max_component is sub_component1  # component upper bounding the version

    # 2. component sets lower bound
    class MySubComponent2(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )

    class MyComponent2(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_1, exclude=True
        )
        value: MySubComponent2

    sub_component2 = MySubComponent2(name="sub_component")
    component2 = MyComponent2(name="component", value=sub_component2)
    max_version, max_component = component2._get_max_agentspec_version_and_component()

    assert max_version == component2.max_agentspec_version
    assert max_component is component2  # component upper bounding the version


def test_deserialize_raises_error_on_invalid_agentspec_version() -> None:
    class MySubComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_1, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_1, exclude=True
        )

    class MyComponent(Component):
        min_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_3_0, exclude=True
        )
        max_agentspec_version: AgentSpecVersionEnum = Field(
            default=AgentSpecVersionEnum.v25_4_1, exclude=True
        )
        value: MySubComponent

    sub_component = MySubComponent(name="sub_component")
    component = MyComponent(name="component", value=sub_component)

    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={
            MyComponent.__name__: MyComponent,
            MySubComponent.__name__: MySubComponent,
        }
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={
            MyComponent.__name__: MyComponent,
            MySubComponent.__name__: MySubComponent,
        }
    )
    obj_as_dict = AgentSpecSerializer(plugins=[serialization_plugin]).to_dict(component)

    assert (
        AGENTSPEC_VERSION_FIELD_NAME in obj_as_dict
        and obj_as_dict[AGENTSPEC_VERSION_FIELD_NAME] == AgentSpecVersionEnum.v25_3_1.value
    )

    obj_as_dict[AGENTSPEC_VERSION_FIELD_NAME] = AgentSpecVersionEnum.v25_4_1.value
    # ^ intentionally modifying the version to check that an error is triggered

    with pytest.raises(
        ValueError,
        match=(
            "Invalid agentspec_version: component agentspec_version=AgentSpecVersionEnum.v25_4_1 but the "
            "maximum allowed version is AgentSpecVersionEnum.v25_3_1 .*'sub_component'"  # <-- upper bounded by
        ),
    ):
        _ = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_dict(obj_as_dict)


def test_agentspec_version_json_schema_contains_correct_enum_values(simplest_flow: Flow) -> None:
    schema = simplest_flow.model_json_schema()
    agentspec_version_values = sorted(
        [e.value for e in AgentSpecVersionEnum if e.value not in _LEGACY_AGENTSPEC_VERSIONS]
    )
    assert agentspec_version_values == sorted(
        schema["$defs"][AgentSpecVersionEnum.__name__]["enum"]
    )


def test_legacy_version_field_name_can_be_loaded(simplest_flow: Flow) -> None:
    serialized_flow = AgentSpecSerializer().to_dict(simplest_flow)
    serialized_flow[_LEGACY_VERSION_FIELD_NAME] = serialized_flow.pop(AGENTSPEC_VERSION_FIELD_NAME)
    deserialized_flow = AgentSpecDeserializer().from_dict(serialized_flow)
    assert deserialized_flow.min_agentspec_version == AgentSpecVersionEnum(
        serialized_flow[_LEGACY_VERSION_FIELD_NAME]
    )


def test_legacy_version_spec_can_be_loaded_and_warns(simplest_flow: Flow) -> None:
    serialized_flow = AgentSpecSerializer().to_dict(simplest_flow)
    serialized_flow[AGENTSPEC_VERSION_FIELD_NAME] = AgentSpecVersionEnum.v25_4_0.value
    with pytest.warns(UserWarning, match="Using a pre-release `agentspec_version`"):
        deserialized_flow = AgentSpecDeserializer().from_dict(serialized_flow)
    assert deserialized_flow == simplest_flow
