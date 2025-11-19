# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Dict, Optional

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import Component
from pyagentspec.remoteagent import RemoteAgent
from pyagentspec.versioning import AgentSpecVersionEnum


class A2ASessionParameters(BaseModel):
    """Class to specify parameters of the A2A session."""

    timeout: float = 60.0
    """The maximum time in seconds to wait for a response before considering the session timed out."""

    poll_interval: float = 2.0
    """The time interval in seconds between polling attempts to check for a response from the server."""

    max_retries: int = 5
    """The maximum number of retry attempts to establish a connection or receive a response before giving up."""


class A2AConnectionConfig(Component):
    """Class to specify configuration settings for establishing a connection in A2A communication."""

    timeout: float = 600.0
    """The maximum time in seconds to wait for HTTP requests to complete before timing out."""

    headers: Optional[Dict[str, str]] = None
    """A dictionary of HTTP headers to include in requests sent to the server."""

    verify: bool = True
    """Determines whether the client verifies the server's SSL certificate, enabling HTTPS.
       If True, the client will verify the server's identity using the provided `ssl_ca_cert`.
       If False, disables SSL verification (not recommended for production environments)."""

    key_file: Optional[str] = None
    """Path to the client's private key file in PEM format, used for mTLS authentication."""

    cert_file: Optional[str] = None
    """Path to the client's certificate chain file in PEM format, used for mTLS authentication."""

    ssl_ca_cert: Optional[str] = None
    """Path to the trusted CA certificate file in PEM format, used to verify the server's identity."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )


class A2AAgent(RemoteAgent):
    """
    Component which communicates with a remote server agent using the A2A Protocol.
    """

    agent_url: str
    """The URL of the remote server agent to connect to."""

    connection_config: A2AConnectionConfig
    """Configuration settings for establishing HTTP connections, including timeout and security parameters."""

    session_parameters: A2ASessionParameters = A2ASessionParameters()
    """Parameters controlling session behavior such as polling timeouts and retry logic."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v25_4_2, init=False, exclude=True
    )
