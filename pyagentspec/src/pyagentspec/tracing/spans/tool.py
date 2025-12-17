# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.tools import Tool
from pyagentspec.tracing.spans.span import Span


class ToolExecutionSpan(Span):
    """
    Span that covers a tool execution. This does not include client tools.

    - Starts when: tool execution starts
    - Ends when: the tool execution is completed and the result is ready to be processed
    """

    tool: Tool
    "The Tool being executed"
