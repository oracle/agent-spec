# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Module containing helper functions used to extract placeholders."""

import re
from typing import List

from pyagentspec.property import Property

TEMPLATE_PLACEHOLDER_REGEXP = r"{{\s*(\w+)\s*}}"


def get_placeholders_from_string(string_with_placeholders: str) -> List[str]:
    """Extract the placeholder names from a string."""
    return list(
        {
            match.strip()
            for match in re.findall(TEMPLATE_PLACEHOLDER_REGEXP, string_with_placeholders)
        }
    )


def get_placeholder_properties_from_string(
    string_with_placeholders: str,
) -> List[Property]:
    """Get the property descriptions for the placeholder names extracted from a string."""
    return [
        Property(
            json_schema={
                "title": placeholder,
                "type": "string",
            }
        )
        for placeholder in get_placeholders_from_string(
            string_with_placeholders=string_with_placeholders
        )
    ]
