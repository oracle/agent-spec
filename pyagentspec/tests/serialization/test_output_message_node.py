# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest
from pydantic import ValidationError

from pyagentspec.flows.nodes import OutputMessageNode
from pyagentspec.property import IntegerProperty, StringProperty
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer


def test_output_message_node_inputs_are_inferred_correctly() -> None:
    node = OutputMessageNode(name="output_node", message="{{first}} and then {{second}}")
    assert node.inputs is not None and len(node.inputs) == 2
    assert all(input_.type == "string" for input_ in node.inputs)
    assert {input_.title for input_ in node.inputs} == {"first", "second"}

    node = OutputMessageNode(name="output_node_2", message="Message without placeholders")
    assert node.inputs is not None and len(node.inputs) == 0


def test_can_serialize_and_deserialize_output_message_node() -> None:
    node = OutputMessageNode(name="output_node", message="{{first}} and then {{second}}")
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(node)
    assert "component_type: OutputMessageNode" in serialized_node
    assert "title: first" in serialized_node
    assert "title: second" in serialized_node

    deserialized_node = AgentSpecDeserializer().from_yaml(serialized_node)
    assert deserialized_node == node


def test_wrong_inputs_raise_error() -> None:
    with pytest.raises(ValidationError):
        _ = OutputMessageNode(
            name="output_node",
            message="{{first}} and then {{second}}",
            inputs=[StringProperty(title="wrong")],
        )


def test_wrong_outputs_raise_error() -> None:
    with pytest.raises(ValidationError):
        _ = OutputMessageNode(
            name="output_node", message="Hey!", outputs=[StringProperty(title="a")]
        )
