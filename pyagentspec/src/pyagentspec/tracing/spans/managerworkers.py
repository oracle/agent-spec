# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.tracing.spans.span import Span


class ManagerWorkersExecutionSpan(Span):
    """
    Span to represent the execution of a ManagerWorkers. Can be nested when executing sub-agents.

    - Starts when: manager-workers pattern execution starts
    - Ends when: the manager-workers execution is completed and the result is ready to be processed
    """

    managerworkers: ManagerWorkers
    "The ManagerWorkers being executed"
