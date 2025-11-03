# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module contains the definitions of control/data flow edges used in agentic flows."""

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge

__all__ = [
    "ControlFlowEdge",
    "DataFlowEdge",
]
