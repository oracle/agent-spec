# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""


from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel

from pyagentspec.component import Component, SerializeAsEnum
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class AuthConfig(Component, abstract=True):
    """Base class for Auth configurations."""


class OAuthEndpoints(BaseModel):
    """
    Explicit OAuth endpoint configuration.

    Use this component when endpoint discovery is not available or not desired.
    This groups the relevant endpoints required to execute OAuth authorization
    code flows and token refresh.
    """

    authorization_endpoint: str
    """Authorization endpoint where the user agent is redirected for login and consent."""
    token_endpoint: str
    """Token endpoint where authorization codes (and refresh tokens) are exchanged
        for access tokens."""
    refresh_endpoint: Optional[str] = None
    """Optional endpoint for refresh token requests. If not provided, runtimes
        typically reuse ``token_endpoint`` for refresh."""
    revocation_endpoint: Optional[str] = None
    """Optional endpoint for token revocation."""
    userinfo_endpoint: Optional[str] = None
    """Optional OIDC UserInfo endpoint."""


class PKCEMethod(str, Enum):
    PLAIN = "plain"
    """Code challenge is equal to code verifier."""
    S256 = "S256"
    """Code verifier is hashed using SHA-256. Recommended over the `plain` method"""


class PKCEPolicy(BaseModel):
    """
    Policy configuration for Proof Key for Code Exchange (PKCE).

    PKCE mitigates authorization code interception and injection attacks in
    authorization code flows. Some protocols (such as MCP OAuth) require PKCE.
    """

    required: bool = True
    """If True, the runtime must refuse to proceed if PKCE cannot be used or
        cannot be validated as supported by the authorization server (depending
        on runtime policy and available metadata)."""
    method: SerializeAsEnum[PKCEMethod] = PKCEMethod.S256
    """PKCE challenge method. Defaults to "S256"."""


class OAuthClientConfig(Component):
    """
    OAuth client identity / registration configuration.

    This configuration describes how the runtime establishes the OAuth client
    identity to use with the authorization server. It supports:
    - Pre-registered clients (static client_id/client_secret)
    - Client ID Metadata Documents (URL-formatted client_id)
    - Dynamic client registration (RFC 7591)

    """

    type: Literal["pre_registered", "client_id_metadata_document", "dynamic_registration"]
    """Strategy used to obtain client identity."""

    # Pre-registered client fields
    client_id: Optional[SensitiveField[str]] = None
    """OAuth client identifier (used for pre-registered clients)."""
    client_secret: Optional[SensitiveField[str]] = None
    """OAuth client secret (used for confidential pre-registered clients)."""
    token_endpoint_auth_method: Optional[str] = None
    """Token endpoint authentication method (e.g., ``"client_secret_basic"``,
        ``"client_secret_post"``, ``"private_key_jwt"``, or ``"none"``)."""

    # Client ID Metadata Document field
    client_id_metadata_url: Optional[SensitiveField[str]] = None
    """HTTPS URL used as the OAuth ``client_id`` for Client ID Metadata Documents."""

    # Dynamic registration field
    registration_endpoint: Optional[str] = None
    """Optional dynamic registration endpoint. If omitted, runtimes may obtain it
        from authorization server discovery metadata when available."""

    min_agentspec_version: AgentSpecVersionEnum = AgentSpecVersionEnum.v26_2_0


class ScopePolicy(str, Enum):
    USE_CHALLENGE_OR_SUPPORTED = "use_challenge_or_supported"
    """may prefer scopes indicated by challenges/metadata."""
    FIXED = "fixed"
    """requests exactly the provided scopes."""


class OAuthConfig(AuthConfig):
    """
    Configure OAuth-based authentication for a tool or transport.

    OAuthConfig is a generic configuration that can be used for both MCP servers
    and non-MCP remote API tools. It supports discovery-based configuration (via
    ``issuer``) and explicit endpoints (via ``endpoints``).

    """

    issuer: Optional[str] = None
    """Authorization server issuer URL used for discovery (e.g., OIDC discovery
        or RFC 8414). If provided, runtimes should discover metadata/endpoints."""
    endpoints: Optional[OAuthEndpoints] = None
    """Explicit OAuth endpoints. If provided, runtimes should use these endpoints
        directly instead of discovery."""
    client: OAuthClientConfig
    """OAuth client identity / registration configuration."""

    redirect_uri: str
    """Redirect (callback) URI registered with the authorization server."""
    scopes: Optional[Union[str, List[str]]] = None
    """Requested scopes, either as a space-delimited string or a list of scope
        strings."""
    scope_policy: Optional[SerializeAsEnum[ScopePolicy]] = None
    """How the runtime selects scopes."""

    pkce: Optional[PKCEPolicy] = None
    """PKCE policy. For authorization code flows, runtimes should typically set
        this to required with method ``S256``."""
    resource: Optional[str] = None
    """Optional resource indicator value (RFC 8707). If set, runtimes should
        include it in relevant authorization and token requests when applicable."""

    min_agentspec_version: AgentSpecVersionEnum = AgentSpecVersionEnum.v26_2_0
