# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import Optional

from pyagentspec._utils import beta
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.remoteagent import RemoteAgent


@beta
class OpenAiAgent(RemoteAgent):
    """
    An agent is a component that can do several rounds of conversation to solve a task.

    The agent is defined in the OpenAI console and this is only a wrapper to connect to it.
    It can be executed by itself, or be executed in a flow using an AgentNode.

    .. warning::
        ``OpenAiAgent`` is currently in beta and may undergo significant changes.
        The API and behaviour are not guaranteed to be stable and may change in future versions.
    """

    llm_config: OpenAiConfig
    remote_agent_id: Optional[str] = None
