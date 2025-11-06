# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict

import pytest
from langgraph_agentspec_adapter._template_rendering import render_template


@pytest.mark.parametrize(
    "template, inputs, expected",
    [
        ("a", {}, "a"),
        ("{{a}}", {"a": 1}, "1"),
        ("{{ a}} {{b }}", {"a": 1, "b": 2}, "1 2"),
        ("{{ a} {b }}", {"a": 1, "b": 2}, "{{ a} {b }}"),
        ("{{ a}{}{b }}", {"a": 1, "b": 2}, "{{ a}{}{b }}"),
        ("{{ a a a a }}", {"a": 1}, "{{ a a a a }}"),
        ("{{a}}{{b}}{{a}}{{a}}", {"a": 1, "b": 2}, "1211"),
        ("{{ b{{a}} }}{{b1}}", {"a": 1, "b": 2, "b1": 3}, "{{ b1 }}3"),
        ("{{{{a}}}}", {"a": " b ", "b": 2}, "{{ b }}"),
        ("{{a}}{{b}}", {"a": "{{b}}", "b": 2}, "{{b}}2"),
        (
            "Here is the equation: {{a}} plus {{b}} equals {{c}}",
            {"a": "{{", "b": "}}", "plus": "SECRET"},
            "Here is the equation: {{ plus }} equals {{c}}",
        ),
        ("{{a}}{{b}}", {"a": "{{sec", "b": "ret}}", "secret": "SECRET"}, "{{secret}}"),
    ],
)
def test_template_are_properly_rendered(
    template: str, inputs: Dict[str, Any], expected: str
) -> None:
    assert render_template(template, inputs) == expected
