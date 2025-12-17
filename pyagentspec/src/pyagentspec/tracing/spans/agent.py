# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.agent import Agent
from pyagentspec.tracing.spans.span import Span


class AgentExecutionSpan(Span):
    """
    Span to represent the execution of an agent. Can be nested when executing sub-agents.

    - Starts when: agent execution starts
    - Ends when: the agent execution is completed, and the result is ready to be processed
    """

    agent: Agent
    "The Agent being executed"
