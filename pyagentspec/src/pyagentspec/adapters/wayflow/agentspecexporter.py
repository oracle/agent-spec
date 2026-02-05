# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as wayflow is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    from wayflowcore.agentspec import AgentSpecExporter
else:
    AgentSpecExporter = LazyLoader("wayflowcore.agentspec").AgentSpecExporter

__all__ = ["AgentSpecExporter"]
