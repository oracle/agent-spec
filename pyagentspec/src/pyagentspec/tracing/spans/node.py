# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.node import Node
from pyagentspec.tracing.spans.span import Span


class NodeExecutionSpan(Span):
    """
    Span that covers the execution of a Node.

    - Starts when: the node execution starts on the given inputs
    - Ends when: the node execution ends and outputs are ready to be processed
    """

    node: Node
    "The Node being executed"
