# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests for the shared adapter helpers in ``pyagentspec.adapters._utils``."""

from pyagentspec.adapters._utils import is_single_string_output
from pyagentspec.property import IntegerProperty, StringProperty


def test_is_single_string_output() -> None:
    """A lone string output is free text, not a structured field, so adapters read it
    from the final message instead of requesting structured generation."""
    assert is_single_string_output([StringProperty(title="x")]) is True
    assert is_single_string_output([]) is False
    assert is_single_string_output([IntegerProperty(title="n")]) is False
    assert is_single_string_output([StringProperty(title="a"), StringProperty(title="b")]) is False
