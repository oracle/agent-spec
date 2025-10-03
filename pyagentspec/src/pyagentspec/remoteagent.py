# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines the remote agent component."""
from pyagentspec.agenticcomponent import AgenticComponent


class RemoteAgent(AgenticComponent, abstract=True):
    """Represents an agent that is defined and created remotely."""

    pass
