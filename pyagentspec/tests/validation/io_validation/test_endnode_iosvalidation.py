# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest

from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.property import Property


def test_end_node_can_be_defined_with_inputs() -> None:
    property_1 = Property(json_schema={"title": "property_1"})
    property_2 = Property(json_schema={"title": "property_2"})
    end_node = EndNode(name="test_end_node", inputs=[property_1, property_2])
    assert end_node


def test_end_node_can_be_defined_with_outputs() -> None:
    property_1 = Property(json_schema={"title": "property_1"})
    property_2 = Property(json_schema={"title": "property_2"})
    end_node = EndNode(name="test_end_node", outputs=[property_1, property_2])
    assert end_node


def test_end_node_can_be_defined_with_both_inputs_and_outputs() -> None:
    property_1 = Property(json_schema={"title": "property_1"})
    property_2 = Property(json_schema={"title": "property_2"})
    end_node = EndNode(
        name="test_end_node",
        inputs=[property_1, property_2],
        outputs=[property_1, property_2],
    )
    assert end_node


def test_end_node_raises_when_defined_with_incompatible_ios() -> None:
    property_1 = Property(json_schema={"title": "property_1"})
    property_2 = Property(json_schema={"title": "property_2"})
    not_property_2 = Property(json_schema={"title": "not_property_2"})
    with pytest.raises(
        ValueError,
        match="If both inputs and outputs are specified for an EndNode, they must be equal",
    ):
        EndNode(
            name="test_end_node",
            inputs=[property_1, property_2],
            outputs=[property_1, not_property_2],
        )
