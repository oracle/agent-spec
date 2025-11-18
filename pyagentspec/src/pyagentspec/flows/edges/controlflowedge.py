# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines control flow edges that can be used in flows."""

from typing import Optional

from pydantic import SerializeAsAny

from pyagentspec.component import Component
from pyagentspec.flows.node import Node


class ControlFlowEdge(Component):
    """
    A control flow edge specifies a possible transition from a node to another in a flow.

    A single node can have several potential next nodes, in which case several control flow edges
    should be present in the control flow connections of that flow.
    """

    from_node: SerializeAsAny[Node]  # See for context
    """The instance of the source Node"""
    from_branch: Optional[str] = None
    """The name of the branch to connect.
    It must be among the list of branches offered by the from_node"""
    to_node: SerializeAsAny[Node]  # See for context
    """The instance of the destination Node"""
