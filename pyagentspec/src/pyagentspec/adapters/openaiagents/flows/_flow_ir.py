# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class IRControlEdge:
    from_id: str
    to_id: str
    branch: str | None = None


@dataclass
class IRDataEdge:
    source_id: str
    source_output: str
    dest_id: str
    dest_input: str


@dataclass
class IRNode:
    id: str
    name: str
    kind: Literal["start", "end", "agent", "llm", "tool", "branch", "message"]
    meta: dict[str, Any]


@dataclass
class IRFlow:
    name: str
    start_id: str
    nodes: list[IRNode] = field(default_factory=list)
    edges_control: list[IRControlEdge] = field(default_factory=list)
    edges_data: list[IRDataEdge] = field(default_factory=list)
