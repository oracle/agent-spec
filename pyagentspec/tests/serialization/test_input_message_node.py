# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest
from pydantic import ValidationError

from pyagentspec.flows.nodes import InputMessageNode
from pyagentspec.property import IntegerProperty, StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


def test_input_message_node_output_is_inferred_correctly() -> None:
    node = InputMessageNode(name="input_node")
    assert node.outputs is not None
    assert len(node.outputs) == 1
    assert isinstance(node.outputs[0], StringProperty)
    assert node.outputs[0].title == node.DEFAULT_OUTPUT

    node = InputMessageNode(name="input_node_2", outputs=[StringProperty(title="a")])
    assert node.outputs is not None
    assert len(node.outputs) == 1
    assert node.outputs[0].type == "string"
    assert node.outputs[0].title == "a"


@pytest.mark.parametrize(
    "message, input_names",
    [
        ("Message!", []),
        ("Hey {{username}}!", ["username"]),
        ("Hey {{username}}, do you know {{myname}}?", ["username", "myname"]),
    ],
)
def test_input_message_node_inputs_are_inferred_correctly(message, input_names) -> None:
    node = InputMessageNode(name="input_node", message=message)
    assert node.inputs is not None
    assert len(node.inputs) == len(input_names)
    assert {property_.title for property_ in node.inputs} == set(input_names)


def test_can_serialize_and_deserialize_input_message_node() -> None:
    node = InputMessageNode(name="input_node", message=None, outputs=[StringProperty(title="a")])
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "component_type: InputMessageNode" in serialized_node
    assert "title: a" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert deserialized_node == node


def test_can_serialize_and_deserialize_input_message_node_with_message() -> None:
    node = InputMessageNode(name="input_node", message="Hey!", outputs=[StringProperty(title="a")])
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "component_type: InputMessageNode" in serialized_node
    assert "title: a" in serialized_node
    assert "message: Hey!" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert deserialized_node == node


def test_wrong_inputs_raise_error() -> None:
    with pytest.raises(ValidationError):
        _ = InputMessageNode(name="input_node", inputs=[StringProperty(title="a")])
    with pytest.raises(ValidationError):
        _ = InputMessageNode(name="input_node", message="{{b}}", inputs=[StringProperty(title="a")])


def test_wrong_outputs_raise_error() -> None:
    with pytest.raises(ValidationError):
        _ = InputMessageNode(name="input_node", outputs=[])
    with pytest.raises(ValidationError):
        _ = InputMessageNode(name="input_node", outputs=[IntegerProperty(title="a")])
