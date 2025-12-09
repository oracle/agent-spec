# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Annotated, TypeAlias, TypeVar

from pydantic.fields import FieldInfo

T = TypeVar("T")

SENSITIVE_FIELD_MARKER: str = "SENSITIVE_FIELD_MARKER"

SensitiveField: TypeAlias = Annotated[T, SENSITIVE_FIELD_MARKER]


def is_sensitive_field(field: FieldInfo) -> bool:
    return SENSITIVE_FIELD_MARKER in field.metadata
