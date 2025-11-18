# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.remoteagent import RemoteAgent
from pyagentspec.versioning import AgentSpecVersionEnum


class A2AAgent(RemoteAgent):
    """
    Component which communicates with a remote server agent using the A2A Protocol.
    """

    agent_url: str
    """URL of the served A2A agent"""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )
