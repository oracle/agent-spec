# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.tracing.events.event import Event


class ExceptionRaised(Event):
    """
    This event is recorded whenever an exception occurs.
    """

    exception_type: str
    """Type of the exception"""

    exception_message: SensitiveField[str]
    """Message of the exception"""

    exception_stacktrace: SensitiveField[str] = ""
    """Stacktrace of the exception"""
