# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import List, Type

import pytest

from pyagentspec import Property
from pyagentspec.component import ComponentWithIO
from pyagentspec.property import StringProperty


def create_mock_component_cls_with_defaults(
    inputs: List[Property],
    outputs: List[Property],
) -> Type[ComponentWithIO]:
    class MockComponent(ComponentWithIO):

        def _get_inferred_inputs(self) -> List[Property]:
            return inputs

        def _get_inferred_outputs(self) -> List[Property]:
            return outputs

    return MockComponent


def test_component_with_no_defaults_and_nothing_passed() -> None:
    component_cls = create_mock_component_cls_with_defaults([], [])
    component = component_cls(name="my_component")
    assert component.inputs == []
    assert component.outputs == []


def test_component_with_no_inputs_raises_when_input_is_passed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"The component received a property titled input_1, but expected only properties with"
            r" the titles: \[\]"
        ),
    ):
        component_cls = create_mock_component_cls_with_defaults([], [])
        component_cls(name="my_component", inputs=[StringProperty(title="input_1")])


def test_component_with_inputs_works_when_passed_correct_input() -> None:
    component_cls = create_mock_component_cls_with_defaults([StringProperty(title="input_1")], [])
    component = component_cls(name="my_component", inputs=[StringProperty(title="input_1")])
    assert component.inputs == [StringProperty(title="input_1")]


def test_component_with_inputs_raises_when_missing_inputs_are_not_passed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"The component expected a property titled input_2, but none of the passed "
            r"properties have this title:"
        ),
    ):
        component_cls = create_mock_component_cls_with_defaults(
            [StringProperty(title="input_1"), StringProperty(title="input_2")], []
        )
        component_cls(name="my_component", inputs=[StringProperty(title="input_1")])


def test_component_with_non_unique_inputs_raises() -> None:
    with pytest.raises(
        ValueError,
        match=r".*Found multiple instances of properties \(inputs or outputs\) with the same title in a ComponentWithIO.*",
    ):
        component_cls = create_mock_component_cls_with_defaults(
            [StringProperty(title="input_1"), StringProperty(title="input_2")], []
        )
        component_cls(
            name="my_component",
            inputs=[StringProperty(title="input_1"), StringProperty(title="input_1")],
        )


def test_component_with_no_outputs_raises_when_output_is_passed() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"The component received a property titled output_1, but expected only properties with"
            r" the titles: \[\]"
        ),
    ):
        component_cls = create_mock_component_cls_with_defaults([], [])
        component_cls(name="my_component", outputs=[StringProperty(title="output_1")])


def test_component_with_outputs_works_when_passed_correct_output() -> None:
    component_cls = create_mock_component_cls_with_defaults([], [StringProperty(title="output_1")])
    component = component_cls(name="my_component", outputs=[StringProperty(title="output_1")])
    assert component.outputs == [StringProperty(title="output_1")]


def test_component_raises_when_specified_outputs_are_incomplete() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"The component expected a property titled output_2, but none of the passed properties"
            r" have this title: \['output_1'\]"
        ),
    ):
        component_cls = create_mock_component_cls_with_defaults(
            [], [StringProperty(title="output_1"), StringProperty(title="output_2")]
        )
        component_cls(name="my_component", outputs=[StringProperty(title="output_1")])


def test_component_with_non_unique_outputs_raises() -> None:
    with pytest.raises(
        ValueError,
        match=r".*Found multiple instances of properties \(inputs or outputs\) with the same title in a ComponentWithIO.*",
    ):
        component_cls = create_mock_component_cls_with_defaults(
            [], [StringProperty(title="output_1"), StringProperty(title="output_2")]
        )
        component_cls(
            name="my_component",
            outputs=[StringProperty(title="output_1"), StringProperty(title="output_1")],
        )
