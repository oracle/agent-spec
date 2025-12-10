# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define MCP configuration abstraction and concrete classes for connecting to MCP servers."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import Self

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.validation_helpers import model_validator_with_error_accumulation
from pyagentspec.versioning import AgentSpecVersionEnum


class SessionParameters(BaseModel):
    """Class to specify parameters of the MCP client session."""

    read_timeout_seconds: float = 60.0
    """How long, in seconds, to wait for a network read before
    aborting the operation."""


class ClientTransport(Component, abstract=True):
    """
    Base class for different MCP client transport mechanisms.

    A Transport is responsible for establishing and managing connections
    to an MCP server, and providing a ClientSession within an async context.
    """

    session_parameters: SessionParameters = Field(default_factory=SessionParameters)
    """Arguments for the MCP session."""


class StdioTransport(ClientTransport):
    """
    Base transport for connecting to an MCP server via subprocess with stdio.

    This is a base class that can be subclassed for specific command-based
    transports like Python, Node, Uvx, etc.

    .. warning::
        Stdio should be used for local prototyping only.
    """

    command: str
    """The executable to run to start the server."""
    args: List[str] = Field(default_factory=list)
    """Command line arguments to pass to the executable."""
    env: Optional[Dict[str, str]] = None
    """
    The environment to use when spawning the process.

    If not specified, the result of get_default_environment() will be used.
    """
    cwd: Optional[str] = None
    """The working directory to use when spawning the process."""


class RemoteTransport(ClientTransport, abstract=True):
    """Base transport class for transport with all remotely hosted servers."""

    url: str
    """The URL of the server."""
    headers: Optional[Dict[str, str]] = None
    """The headers to send to the server."""
    sensitive_headers: SensitiveField[Optional[Dict[str, str]]] = None
    """Additional headers to send to the server.
       These headers are intended to be used for sensitive information such as
       authentication tokens and will be excluded form exported JSON configs."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("sensitive_headers")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.sensitive_headers:
            # `api_key` is only introduced starting from 25.4.2
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(parent_min_version, current_object_min_version)

    @model_validator_with_error_accumulation
    def _validate_sensitive_headers_are_disjoint(self) -> Self:
        repeated_headers = set(self.headers or {}).intersection(set(self.sensitive_headers or {}))
        if repeated_headers:
            raise ValueError(
                f"Found some headers have been specified in both `headers` and "
                f"`sensitive_headers`: {repeated_headers}"
            )
        return self


class SSETransport(RemoteTransport):
    """Transport implementation that connects to an MCP server via Server-Sent Events."""


class SSEmTLSTransport(SSETransport):
    """
    Transport layer for SSE with mTLS (mutual Transport Layer Security).

    This transport establishes a secure, mutually authenticated TLS connection to the MCP server using client
    certificates. Production deployments MUST use this transport to ensure both client and server identities
    are verified.

    Notes
    -----
    - Users MUST provide a valid client certificate (PEM format) and private key.
    - Users MUST provide (or trust) the correct certificate authority (CA) for the server they're connecting to.
    - The client certificate/key and CA certificate paths can be managed via secrets, config files, or secure
      environment variables in any production system.
    - Executors should ensure that these files are rotated and managed securely.

    """

    key_file: SensitiveField[str]
    """The path to the client's private key file (PEM format). If None, mTLS cannot be performed."""
    cert_file: SensitiveField[str]
    """The path to the client's certificate chain file (PEM format). If None, mTLS cannot be performed."""
    ca_file: SensitiveField[str]
    """The path to the trusted CA certificate file (PEM format) to verify the server.
    If None, system cert store is used."""


class StreamableHTTPTransport(RemoteTransport):
    """Transport implementation that connects to an MCP server via Streamable HTTP."""


class StreamableHTTPmTLSTransport(StreamableHTTPTransport):
    """
    Transport layer for streamable HTTP with mTLS (mutual Transport Layer Security).

    This transport establishes a secure, mutually authenticated TLS connection to the MCP server using client
    certificates. Production deployments MUST use this transport to ensure both client and server identities
    are verified.

    Notes
    -----
    - Users MUST provide a valid client certificate (PEM format) and private key.
    - Users MUST provide (or trust) the correct certificate authority (CA) for the server they're connecting to.
    - The client certificate/key and CA certificate paths can be managed via secrets, config files, or secure
      environment variables in any production system.
    - Executors should ensure that these files are rotated and managed securely.

    """

    key_file: SensitiveField[str]
    """The path to the client's private key file (PEM format). If None, mTLS cannot be performed."""
    cert_file: SensitiveField[str]
    """The path to the client's certificate chain file (PEM format). If None, mTLS cannot be performed."""
    ca_file: SensitiveField[str]
    """The path to the trusted CA certificate file (PEM format) to verify the server.
    If None, system cert store is used."""
