# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
from typing import Any, Dict, List, Tuple

from pyagentspec.templating import TEMPLATE_PLACEHOLDER_REGEXP


def render_nested_object_template(
    object: Any,
    inputs: Dict[str, Any],
) -> Any:
    """Renders any found variables between curly braces from any string in an object which can be an arbitrarily nested
    structure of dicts, lists, sets and tuples.

    Parameters
    ----------
    object : Any
        A potentially nested python object (str, bytes, dict, list, set, tuple)
    inputs : Dict[str, Any]
        The inputs to the variables

    Returns
    -------
    Any
        An object of the same type as the input object with all found template variables
        replaced according to the given inputs.

    """
    if isinstance(object, str):
        return render_template(object, inputs)
    elif isinstance(object, bytes):
        return render_nested_object_template(
            object.decode("utf-8", errors="replace"),
            inputs,
        )
    elif isinstance(object, dict):
        return {
            render_nested_object_template(
                k,
                inputs,
            ): render_nested_object_template(
                v,
                inputs,
            )
            for k, v in object.items()
        }
    elif isinstance(object, list) or isinstance(object, set) or isinstance(object, tuple):
        return object.__class__(
            [
                render_nested_object_template(
                    item,
                    inputs,
                )
                for item in object
            ]
        )
    else:
        return object


def render_template(template: str, inputs: Dict[str, Any]) -> str:
    """Render a prompt template using inputs."""
    if not isinstance(template, str):
        return str(template)
    return _recursive_template_splitting_rendering(
        template, [(input_title, input_value) for input_title, input_value in inputs.items()]
    )


def _recursive_template_splitting_rendering(template: str, inputs: List[Tuple[str, Any]]) -> str:
    """Recursively split and join the templates using the list of inputs."""
    if len(inputs) == 0:
        return template
    input_title, input_value = inputs[-1]
    splitting_regexp = TEMPLATE_PLACEHOLDER_REGEXP.replace(r"(\w+)", input_title)
    split_templates = re.split(splitting_regexp, template)
    rendered_split_templates = [
        _recursive_template_splitting_rendering(t, inputs[:-1]) for t in split_templates
    ]
    rendered_template = str(input_value).join(rendered_split_templates)
    return rendered_template
