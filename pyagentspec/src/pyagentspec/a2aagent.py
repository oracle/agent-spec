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
