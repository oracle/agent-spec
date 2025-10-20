# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec._utils import beta
from pyagentspec.component import Component
from pyagentspec.property import (
    DictProperty,
    FloatProperty,
    IntegerProperty,
    ListProperty,
    ObjectProperty,
    StringProperty,
    UnionProperty,
)


def test_beta_decorator_raises_warning_only_on_first_instantiation() -> None:
    @beta
    class A(Component):
        pass

    with pytest.warns(UserWarning, match="is currently in beta and may undergo"):
        A(name="a")
    A(name="a")


def test_beta_decorator_raises_warning_on_first_instantiation_of_each_class() -> None:
    @beta
    class A(Component):
        pass

    @beta
    class B(Component):
        pass

    with pytest.warns(UserWarning, match="is currently in beta and may undergo"):
        A(name="a")
    A(name="a")

    with pytest.warns(UserWarning, match="is currently in beta and may undergo"):
        B(name="b")
    B(name="b")
