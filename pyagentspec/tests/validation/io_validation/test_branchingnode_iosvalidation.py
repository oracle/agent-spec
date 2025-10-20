# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.nodes.branchingnode import BranchingNode
from pyagentspec.property import Property


def test_branching_node_has_only_one_str_input_by_default() -> None:
    branching_node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_2": "some_branch_2",
        },
    )
    assert branching_node.inputs and len(branching_node.inputs) == 1
    assert branching_node.outputs == []


def test_branching_node_accepts_renaming_of_input() -> None:
    override_input = Property(json_schema={"title": "nice_branching_input"})
    branching_node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_2": "some_branch_2",
        },
        inputs=[override_input],
    )
    assert branching_node.inputs == [override_input]


def test_branching_node_raises_on_extra_output() -> None:
    extra_output = Property(json_schema={"title": "extra_output"})
    with pytest.raises(ValueError, match="extra_output"):
        BranchingNode(
            name="branching_node_name",
            mapping={
                "some_value_1": "some_branch_1",
                "some_value_2": "some_branch_2",
            },
            outputs=[extra_output],
        )


# TODO test_branching_node_accepts_input_with_castable_type
# TODO test_branching_node_raises_on_io_with_incompatible_type
