# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import inspect
import logging
from typing import Dict, List, Optional, Type, TypeVar

from pydantic import VERSION as PYDANTIC_VERSION
from pydantic import BaseModel
from sphinx.application import Sphinx

ComponentTypeT = TypeVar("ComponentTypeT", bound=Type[BaseModel])

logger = logging.getLogger(__name__)


def extract_field_descriptions(cls: Type[BaseModel]) -> Dict[str, str]:
    """
    Extract descriptions for all fields in a Pydantic model.

    Parameters
    ----------
        cls: A Pydantic model class

    Returns
    -------
        Dictionary mapping field names to their descriptions
    """
    result = {}

    if not PYDANTIC_VERSION.startswith("2."):
        raise ValueError(
            "This extension only supports Pydantic v2. Please upgrade your Pydantic version."
        )

    for field_name, field_info in cls.model_fields.items():
        # First try to get description from field info
        description = field_info.description

        # If no description, try to find docstring in class variables
        if not description:
            description = _find_field_docstring(cls, field_name)

        # If still no description, look in parent classes
        if not description:
            description = _find_description_in_parents(cls, field_name)

        result[field_name] = description or ""

    return result


def _find_field_docstring(cls: Type[BaseModel], field_name: str) -> Optional[str]:
    """Find docstring for a class variable by inspecting the class source code."""
    try:
        # Get the source code of the class
        source_lines = inspect.getsourcelines(cls)[0]

        # Look for lines that define the field
        for i, line in enumerate(source_lines):
            stripped_line = line.strip()
            field_def_patterns = [f"{field_name} =", f"{field_name}:", f"{field_name} :"]

            if any(pattern in stripped_line for pattern in field_def_patterns):
                # Check if there's a docstring on the same line
                if '"""' in stripped_line and stripped_line.count('"""') >= 2:
                    # Extract inline docstring
                    parts = stripped_line.split('"""')
                    if len(parts) >= 3:
                        return parts[1].strip()

                # Check if the next line has a docstring
                if i + 1 < len(source_lines):
                    next_line = source_lines[i + 1].strip()

                    # Handle single-line docstring
                    if next_line.startswith('"""') and next_line.endswith('"""'):
                        return next_line.strip('"').strip()

                    # Handle multi-line docstring
                    elif next_line.startswith('"""'):
                        doc_content = []

                        # Skip the opening """
                        doc_content.append(next_line[3:])

                        # Continue until closing """
                        j = i + 2
                        while j < len(source_lines) and '"""' not in source_lines[j]:
                            doc_content.append(source_lines[j].strip())
                            j += 1

                        # Add the last line until """
                        if j < len(source_lines):
                            last_line = source_lines[j].split('"""', 1)[0]
                            if last_line:
                                doc_content.append(last_line.strip())

                        return "\n".join(doc_content).strip()
    except (OSError, TypeError):
        pass

    return None


def _find_description_in_parents(cls: Type[BaseModel], field_name: str) -> Optional[str]:
    """Search parent classes for field descriptions."""
    # Get all parent classes except BaseModel
    mro = cls.__mro__
    parent_classes = [c for c in mro[1:] if c != BaseModel and issubclass(c, BaseModel)]

    for parent in parent_classes:
        # Check if field exists in parent
        if hasattr(parent, "model_fields") and field_name in parent.model_fields:
            # Try to get description from field info
            description = parent.model_fields[field_name].description
            if description:
                return description

            # Try to get docstring
            doc = _find_field_docstring(parent, field_name)
            if doc:
                return doc

    return None


def autodoc_process_docstring(app: Sphinx, what, name, obj, options, lines: List[str]):
    from pyagentspec.component import AbstractableModel

    if not (what == "class" and issubclass(obj, AbstractableModel)):
        return

    try:
        field_descriptions = extract_field_descriptions(obj)
        if not field_descriptions:
            return lines

        split_idx = next(
            (i for i, line in enumerate(lines) if line.strip() == ".. rubric:: Example"), -1
        )
        param_lines = (
            [""]
            + [
                f":param {field_name}: {description}"
                for field_name, description in field_descriptions.items()
            ]
            + [""]
        )
        # Insert parameter lines into the list
        lines[split_idx:split_idx] = param_lines

    except Exception as e:
        logger.warning("Error documenting %s: %s", obj.__name__, str(e))


def setup(app: Sphinx):
    app.connect("autodoc-process-docstring", autodoc_process_docstring)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
