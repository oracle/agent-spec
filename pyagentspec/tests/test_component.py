# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import pytest
from pydantic import ValidationError

from pyagentspec import Component


class ConcreteChildOfComponent(Component):
    existing_attribute: str = ""


def test_missing_component_name_raises_exception() -> None:
    with pytest.raises(ValidationError, match="name\n  Field required"):
        ConcreteChildOfComponent(existing_attribute="abcde")  # type: ignore


def test_unexpected_attribute_of_component_raises_exception() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ConcreteChildOfComponent(
            name="abcd", existing_attribute="abcde", nonexisting_attribute="error!"  # type: ignore
        )


def test_component_equality() -> None:
    a = ConcreteChildOfComponent(name="a", id="a")
    b = ConcreteChildOfComponent(name="b")
    c = ConcreteChildOfComponent(name="a")
    d = ConcreteChildOfComponent(name="a", id="a")
    e = ConcreteChildOfComponent(name="a", id="a", existing_attribute="e")
    assert a == a
    assert a != b
    assert a != c
    assert a == d
    assert a != e
