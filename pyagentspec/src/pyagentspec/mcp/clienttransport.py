# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Define MCP configuration abstraction and concrete classes for connecting to MCP servers."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from pyagentspec.component import Component


class SessionParameters(BaseModel):
    """Class to specify parameters of the MCP client session."""

    read_timeout_seconds: float = 60
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

    key_file: str
    """The path to the client's private key file (PEM format). If None, mTLS cannot be performed."""
    cert_file: str
    """The path to the client's certificate chain file (PEM format). If None, mTLS cannot be performed."""
    ca_file: str
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

    key_file: str
    """The path to the client's private key file (PEM format). If None, mTLS cannot be performed."""
    cert_file: str
    """The path to the client's certificate chain file (PEM format). If None, mTLS cannot be performed."""
    ca_file: str
    """The path to the trusted CA certificate file (PEM format) to verify the server.
    If None, system cert store is used."""
