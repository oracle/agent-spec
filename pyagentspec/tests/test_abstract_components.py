# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from typing import Type

import pytest

from pyagentspec import Component
from pyagentspec.flows.node import Node
from pyagentspec.llms.llmconfig import LlmConfig


def test_component_cannot_be_instantiated() -> None:
    with pytest.raises(
        TypeError, match="Class '.*' is meant to be abstract and cannot be instantiated"
    ):
        Component(name="abcde")


def test_concrete_child_of_component_can_be_instantiated() -> None:
    class ConcreteChildOfComponent(Component):
        pass

    assert ConcreteChildOfComponent(name="abcde") is not None


def test_abstract_child_of_component_cannot_be_instantiated() -> None:
    class AbstractChildOfComponent(Component, abstract=True):
        pass

    with pytest.raises(
        TypeError, match="Class '.*' is meant to be abstract and cannot be instantiated"
    ):
        AbstractChildOfComponent(name="abcde")


def test_abstract_child_of_concrete_component_cannot_be_instantiated() -> None:
    class ConcreteChildOfComponent(Component):
        pass

    class AbstractChildOfConcreteComponent(ConcreteChildOfComponent, abstract=True):
        pass

    with pytest.raises(
        TypeError, match="Class '.*' is meant to be abstract and cannot be instantiated"
    ):
        AbstractChildOfConcreteComponent(name="abcde")


def test_concrete_child_of_concrete_component_can_be_instantiated() -> None:
    class ConcreteChildOfComponent(Component):
        pass

    class ContcreteChildOfConcreteComponent(ConcreteChildOfComponent):
        pass

    assert ContcreteChildOfConcreteComponent(name="abcde") is not None


@pytest.mark.parametrize("expected_abstract_cls", [Component, Node, LlmConfig])
def test_agentspec_components_are_abstract(expected_abstract_cls: Type[Component]) -> None:
    with pytest.raises(
        TypeError, match="Class '.*' is meant to be abstract and cannot be instantiated"
    ):
        expected_abstract_cls(name="abcde")
