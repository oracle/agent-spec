# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Set

import pytest

from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_string


@pytest.mark.parametrize(
    "string,expected_placeholder_names",
    [
        ("", {}),
        ("{{ hello }}{{ ?  }}{{ }}{{ world }}", {"hello", "world"}),
        ("this is my string with a {{placeholder}}", {"placeholder"}),
        (
            "{{var}} Duplicate placeholders should appear once {{var2}} {{var2}} {{var}}",
            {"var", "var2"},
        ),
        (
            "The following is not a {placeholder} but these ones are:"
            " {{first}}, {{second_placeholder}}, {{ Third }}",
            {"first", "second_placeholder", "Third"},
        ),
    ],
)
def test_get_placeholder_properties_from_string_works(
    string: str, expected_placeholder_names: Set[Property]
) -> None:
    placeholder_properties = get_placeholder_properties_from_string(string)
    assert len(placeholder_properties) == len(expected_placeholder_names)
    for placeholder_property in placeholder_properties:
        assert isinstance(placeholder_property, Property)
        assert placeholder_property.json_schema["title"] in expected_placeholder_names
        assert placeholder_property.json_schema["type"] == "string"
