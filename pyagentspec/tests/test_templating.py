# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Set

import pytest

from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_json_object


@pytest.mark.parametrize(
    "templated_object,expected_placeholder_names",
    [
        ("", set()),
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
        (b"byte {{b}}", {"b"}),
        ({"{{k1}}": "value {{v1}}", "normal": "no"}, {"k1", "v1"}),
        ([{"a": "{{x}}"}, ["nested {{y}}", {"z": "{{z}}"}]], {"x", "y", "z"}),
        (("{{dup}}", "{{dup}}", {"inner": "{{inner}}"}), {"dup", "inner"}),
        ({"set_{{s1}}", "no_placeholder"}, {"s1"}),
        ({"outer": {"inner": "{{deep}}"}}, {"deep"}),
        (["no", 123, None, "{{ok}}"], {"ok"}),
        # More complex nested cases
        (
            {
                "level1": [
                    {"level2": "value {{deep1}} and {{deep2}}"},
                    ("tuple {{deep3}}", {"nested": ["{{deep4}}", {"double": "{{deep1}}"}]}),
                ],
                "{{top}}": "key placeholder",
            },
            {"deep1", "deep2", "deep3", "deep4", "top"},
        ),
        (
            [
                {"bytes": b"b{{bb}}"},
                "str {{ss}}",
                {"inner": (b"b2{{bb2}}", "{{ss}}")},
                {"mixed": [{"x": "{{x1}}"}, [{"y": "{{y1}}"}, ("{{y2}}",)]]},
            ],
            {"bb", "ss", "bb2", "x1", "y1", "y2"},
        ),
        (
            {
                ("{{tk}}", 1): [{"list_item": "{{li}}"}, {"li2": "{{li2}}"}],
                "normal": {"inner_set": {"{{fs}}"}, "value": "no {{v}}"},
            },
            {"tk", "li", "li2", "fs", "v"},
        ),
    ],
)
def test_get_placeholder_properties_from_json_object_works(
    templated_object: Any, expected_placeholder_names: Set[str]
) -> None:
    placeholder_properties = get_placeholder_properties_from_json_object(templated_object)
    assert len(placeholder_properties) == len(expected_placeholder_names)
    inferred_titles = []
    for placeholder_property in placeholder_properties:
        assert isinstance(placeholder_property, Property)
        inferred_titles.append(placeholder_property.json_schema["title"])
        assert placeholder_property.json_schema["type"] == "string"

    assert len(inferred_titles) == len(
        set(inferred_titles)
    )  # There should not be duplicates in inferred properties
    assert (
        set(inferred_titles) == expected_placeholder_names
    )  # Set of inferred titles should match expected properties set
