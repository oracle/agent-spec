# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class FlowConversionError(Exception):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = f"[{self.code}] {self.message}"
        if self.details:
            return f"{base} | details={self.details}"
        return base


class UnsupportedPatternError(FlowConversionError):
    pass


class LossyMappingError(FlowConversionError):
    pass


class RulePackNotFoundError(FlowConversionError):
    pass
