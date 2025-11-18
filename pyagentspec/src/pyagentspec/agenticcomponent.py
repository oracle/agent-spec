# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the agentic component."""
from pyagentspec.component import ComponentWithIO


class AgenticComponent(ComponentWithIO, abstract=True):
    """Represents a component that can be interacted with, asking questions and getting answers from it."""

    pass
