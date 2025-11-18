# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the OCI Agent component."""

from pydantic import SerializeAsAny

from pyagentspec.llms.ociclientconfig import OciClientConfig
from pyagentspec.remoteagent import RemoteAgent


class OciAgent(RemoteAgent):
    """
    An agent is a component that can do several rounds of conversation to solve a task.

    The agent is defined on the OCI console and this is only a wrapper to connect to it.
    It can be executed by itself, or be executed in a flow using an AgentNode.
    """

    agent_endpoint_id: str
    client_config: SerializeAsAny[OciClientConfig]
