# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.tracing.spans.span import Span


class RootSpan(Span):
    """
    Span that covers a whole Trace.

    - Starts when: a Trace is started
    - Ends when: a Trace is closed
    """
