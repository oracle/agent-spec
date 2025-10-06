# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from typing import List, Optional, Type, Union, cast

import pytest
import yaml

from pyagentspec.component import Component
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.property import Property
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.serialization.builtinsdeserializationplugin import (
    BuiltinsComponentDeserializationPlugin,
)
from pyagentspec.serialization.builtinserializationplugin import (
    BuiltinsComponentSerializationPlugin,
)
from pyagentspec.serialization.pydanticdeserializationplugin import (
    PydanticComponentDeserializationPlugin,
)
from pyagentspec.serialization.pydanticserializationplugin import (
    PydanticComponentSerializationPlugin,
)


class MyCustomNode(Node):
    my_param: str
    """Parameter for the external node"""

    def _get_inferred_inputs(self) -> List[Property]:
        return self.inputs or self.outputs or []

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or self.inputs or []


@pytest.fixture
def flow_with_custom_node() -> Flow:
    start_node = StartNode(id="start", name="start_node")
    custom_node = MyCustomNode(id="custom", name="custom", my_param="my param value")
    end_node = EndNode(id="end", name="end_node")
    return Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, custom_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start::custom", from_node=start_node, to_node=custom_node),
            ControlFlowEdge(name="custom::end", from_node=custom_node, to_node=end_node),
        ],
    )


def test_abstract_components_do_not_appear_in_builtin_plugins() -> None:
    all_supported_types = (
        BuiltinsComponentSerializationPlugin().supported_component_types()
        + BuiltinsComponentDeserializationPlugin().supported_component_types()
    )
    assert all(
        (component_type := Component.get_class_from_name(supported_type))
        and not component_type._is_abstract
        for supported_type in all_supported_types
    )


def test_flow_with_custom_node_raises_on_serialization_with_only_builtin_plugins(
    flow_with_custom_node: Flow,
) -> None:
    flow = flow_with_custom_node
    serializer = AgentSpecSerializer()
    with pytest.raises(
        ValueError,
        match=f"There is no plugin to dump the component type {MyCustomNode.__name__}",
    ):
        _ = serializer.to_yaml(flow)


def test_flow_with_custom_node_can_be_serialized_with_custom_plugin(
    flow_with_custom_node: Flow,
) -> None:
    custom_serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyCustomNode.__name__: MyCustomNode}
    )
    serializer = AgentSpecSerializer(plugins=[custom_serialization_plugin])
    _ = serializer.to_yaml(flow_with_custom_node)


def test_flow_with_custom_node_serializes_with_plugin_information(
    flow_with_custom_node: Flow,
) -> None:
    custom_serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyCustomNode.__name__: MyCustomNode}
    )
    serializer = AgentSpecSerializer(plugins=[custom_serialization_plugin])
    serialized_flow = serializer.to_yaml(flow_with_custom_node)

    flow_as_dict = yaml.safe_load(serialized_flow)
    custom_node_as_dict = flow_as_dict["$referenced_components"]["custom"]
    assert (
        "component_plugin_name" in custom_node_as_dict
        and custom_node_as_dict["component_plugin_name"] == custom_serialization_plugin.plugin_name
    )
    assert (
        "component_plugin_version" in custom_node_as_dict
        and custom_node_as_dict["component_plugin_version"]
        == custom_serialization_plugin.plugin_version
    )


def test_flow_with_custom_node_raises_on_deserialization_with_only_builtin_plugins(
    flow_with_custom_node: Flow,
) -> None:
    flow = flow_with_custom_node
    custom_serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyCustomNode.__name__: MyCustomNode}
    )
    serializer = AgentSpecSerializer(plugins=[custom_serialization_plugin])
    ser_flow = serializer.to_yaml(flow)

    deserializer = AgentSpecDeserializer()
    with pytest.raises(
        ValueError,
        match=f"There is no plugin to load the component type {MyCustomNode.__name__}",
    ):
        _ = deserializer.from_yaml(ser_flow)


def test_flow_with_custom_node_can_be_serialized_and_deserialized_with_custom_plugin(
    flow_with_custom_node: Flow,
) -> None:
    custom_serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyCustomNode.__name__: MyCustomNode}
    )
    serializer = AgentSpecSerializer(plugins=[custom_serialization_plugin])
    ser_flow = serializer.to_yaml(flow_with_custom_node)

    custom_deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={MyCustomNode.__name__: MyCustomNode}
    )
    deserializer = AgentSpecDeserializer(plugins=[custom_deserialization_plugin])
    deser_flow: Flow = cast(Flow, deserializer.from_yaml(ser_flow))

    deser_custom_node = deser_flow.nodes[1]
    original_custom_node = flow_with_custom_node.nodes[1]
    assert deser_custom_node == original_custom_node


def test_serialization_raises_on_two_plugins_for_a_same_component() -> None:
    extra_serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={StartNode.__name__: StartNode}
    )
    with pytest.raises(
        ValueError, match="Several plugins are handling the serialization of the same types"
    ):
        _ = AgentSpecSerializer(plugins=[extra_serialization_plugin])


def test_deserialization_raises_on_two_plugins_for_a_same_component() -> None:
    extra_deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={StartNode.__name__: StartNode}
    )
    with pytest.raises(
        ValueError, match="Several plugins are handling the deserialization of the same types"
    ):
        _ = AgentSpecDeserializer(plugins=[extra_deserialization_plugin])


class MySubComponent(Component):
    pass


class MyComponent1(Component):
    value: Optional[Union[List[MySubComponent], MySubComponent, str]] = None


def _assert_values_correctness_and_equality(
    deser_value: Optional[Union[List[MySubComponent], MySubComponent, str]],
    expected_value: Optional[Union[List[MySubComponent], MySubComponent, str]],
    expected_value_type: Union[
        Type[List[MySubComponent]], Type[MySubComponent], Type[str], Type[None]
    ],
) -> None:
    assert isinstance(deser_value, expected_value_type)

    if isinstance(deser_value, list) and isinstance(expected_value, list):
        assert len(deser_value) == len(expected_value)
        for item1, item2 in zip(deser_value, expected_value):
            assert item1.name == item2.name
    elif isinstance(deser_value, MySubComponent) and isinstance(expected_value, MySubComponent):
        assert deser_value.name == expected_value.name
    elif isinstance(deser_value, str) and isinstance(expected_value, str):
        assert deser_value == expected_value
    elif isinstance(deser_value, type(None)) and isinstance(expected_value, type(None)):
        pass
    else:
        raise ValueError("Incorrect type", deser_value)


@pytest.mark.parametrize(
    "value,expected_value_type",
    [
        ([MySubComponent(name="my_sub_component")], list),
        (MySubComponent(name="my_sub_component"), MySubComponent),
        ("my_sub_component", str),
        (None, type(None)),
    ],
)
def test_component_field_serialization_works_with_joint_union_and_optional_types(
    value: Optional[Union[List[MySubComponent], MySubComponent, str]],
    expected_value_type: Union[
        Type[List[MySubComponent]], Type[MySubComponent], Type[str], Type[None]
    ],
) -> None:
    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={
            MyComponent1.__name__: MyComponent1,
            MySubComponent.__name__: MySubComponent,
        }
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={
            MyComponent1.__name__: MyComponent1,
            MySubComponent.__name__: MySubComponent,
        }
    )

    for _ in range(100):  # takes 10ms
        component = MyComponent1(
            name="my_component",
            value=value,
        )
        ser_obj = AgentSpecSerializer(plugins=[serialization_plugin]).to_json(component)
        deser_obj = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_json(ser_obj)

        assert isinstance(deser_obj, MyComponent1)
        _assert_values_correctness_and_equality(
            deser_value=deser_obj.value,
            expected_value=value,
            expected_value_type=expected_value_type,
        )


class MyComponent2(Component):
    value: Union[str, MySubComponent]


@pytest.mark.parametrize(
    "value,expected_value_type",
    [("my_sub_component", str), (MySubComponent(name="my_sub_component"), MySubComponent)],
)
def test_component_field_deserializes_properly_with_union_and_str_type(
    value: Union[str, MySubComponent],
    expected_value_type: Union[Type[str], Type[MySubComponent]],
) -> None:
    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={
            MyComponent2.__name__: MyComponent2,
            MySubComponent.__name__: MySubComponent,
        }
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={
            MyComponent2.__name__: MyComponent2,
            MySubComponent.__name__: MySubComponent,
        }
    )
    for _ in range(100):  # takes 10ms
        component = MyComponent2(
            name="my_component",
            value=value,
        )
        ser_obj = AgentSpecSerializer(plugins=[serialization_plugin]).to_json(component)
        deser_obj = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_json(ser_obj)

        assert isinstance(deser_obj, MyComponent2)
        _assert_values_correctness_and_equality(
            deser_value=deser_obj.value,
            expected_value=value,
            expected_value_type=expected_value_type,
        )


class MyComponent3(Component):
    value: Optional[Union[str, None]] = None


@pytest.mark.parametrize(
    "value,expected_value_type",
    [
        ("test_string", str),
        (None, type(None)),
    ],
)
def test_component_field_serialization_with_optional_union_str_none(
    value: Optional[Union[str, None]],
    expected_value_type: Union[Type[str], Type[None]],
) -> None:
    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyComponent3.__name__: MyComponent3}
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={MyComponent3.__name__: MyComponent3}
    )
    for _ in range(100):
        component = MyComponent3(
            name="my_component",
            value=value,
        )
        ser_obj = AgentSpecSerializer(plugins=[serialization_plugin]).to_json(component)
        deser_obj = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_json(ser_obj)

        assert isinstance(deser_obj, MyComponent3)
        _assert_values_correctness_and_equality(
            deser_value=deser_obj.value,
            expected_value=value,
            expected_value_type=expected_value_type,
        )


class MyComponent4(Component):
    value: Union[str, Union[int, float]]


@pytest.mark.parametrize(
    "value,expected_value_type",
    [
        ("a string", str),
        (123, int),
        (4.56, float),
    ],
)
def test_component_field_serialization_with_union_str_int_float(
    value: Union[str, int, float],
    expected_value_type: Union[Type[str], Type[int], Type[float]],
) -> None:
    serialization_plugin = PydanticComponentSerializationPlugin(
        component_types_and_models={MyComponent4.__name__: MyComponent4}
    )
    deserialization_plugin = PydanticComponentDeserializationPlugin(
        component_types_and_models={MyComponent4.__name__: MyComponent4}
    )
    for _ in range(100):
        component = MyComponent4(name="my_component", value=value)
        ser_obj = AgentSpecSerializer(plugins=[serialization_plugin]).to_json(component)
        deser_obj = AgentSpecDeserializer(plugins=[deserialization_plugin]).from_json(ser_obj)

        assert isinstance(deser_obj, MyComponent4)
        assert isinstance(deser_obj.value, expected_value_type)
        assert deser_obj.value == value
