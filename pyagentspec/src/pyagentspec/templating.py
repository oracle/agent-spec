# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Module containing helper functions used to extract placeholders."""

import re
from collections import Counter
from typing import Any, List

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
    """Get the property descriptions for the placeholder names extracted from a string (backwards compatible)."""
    return get_placeholder_properties_from_json_object(string_with_placeholders)


def get_placeholder_properties_from_json_object(
    object: Any,
) -> List[Property]:
    """Get the property descriptions for the placeholder names extracted from a JSON serializable object (with nested inputs)."""
    return [
        Property(
            json_schema={
                "title": placeholder,
                "type": "string",
            }
        )
        for placeholder in get_placeholders_from_json_object(object=object)
    ]


def get_placeholders_from_json_object(
    object: Any,
) -> List[str]:
    """Retrieve the used variable names from any python object.
    Recursively traverses dicts, lists, sets, tuples, etc. and collects all templated variables in found strings and byte sequences.

    Parameters
    ----------
    object : Any
        A potentially nested python object (str, bytes, dict, list, set, tuple)

    Returns
    -------
    List[str]
        List of the extracted variable names.
        Note: this list is flattened and does not follow the structure of the inputted object
    """
    if isinstance(object, str):
        return get_placeholders_from_string(object)
    elif isinstance(object, bytes):
        return get_placeholders_from_json_object(object.decode("utf-8", errors="replace"))
    elif isinstance(object, dict):
        key_templates = get_placeholders_from_json_object(list(object.keys()))
        value_templates = get_placeholders_from_json_object(list(object.values()))
        return list(set(key_templates + value_templates))
    elif isinstance(object, list) or isinstance(object, set) or isinstance(object, tuple):
        placeholders = Counter(
            nested_placeholder
            for nested_item in object
            for nested_placeholder in get_placeholders_from_json_object(nested_item)
        )
        return list(placeholders)
    else:
        # unknown object reached, ignore
        return []
