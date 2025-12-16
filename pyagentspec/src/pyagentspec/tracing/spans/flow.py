# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.flow import Flow
from pyagentspec.tracing.spans.span import Span


class FlowExecutionSpan(Span):
    """
    Span that covers the execution of a Flow.

    - Starts when: the StartNode execution of this flow starts
    - Ends when: one of the EndNode execution finishes
    """

    flow: Flow
    "The Flow being executed"
