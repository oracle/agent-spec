# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import ssl
import warnings
from typing import Any, Optional

import httpx


class _HttpxClientFactory:
    """Build HTTPX async clients for MCP transports with explicit TLS verification."""

    def __init__(
        self,
        verify: bool = True,
        key_file: Optional[str] = None,
        cert_file: Optional[str] = None,
        ssl_ca_cert: Optional[str] = None,
        check_hostname: bool = True,
        follow_redirects: bool = True,
    ):
        self.verify: bool | ssl.SSLContext
        if verify:
            # When a custom CA is provided, use it as the sole trust anchor (replacing the
            # system CA bundle) so the trust boundary stays exactly as configured.
            # When no custom CA is given, fall back to the system CA bundle.
            if ssl_ca_cert:
                ssl_ctx = ssl.create_default_context(cafile=ssl_ca_cert)
            else:
                ssl_ctx = ssl.create_default_context()

            if key_file or cert_file:
                # Client authentication requires both pieces of certificate material.
                if not (key_file and cert_file):
                    raise ValueError(
                        "When client certificates are provided, both `key_file` and "
                        "`cert_file` must be defined."
                    )
                ssl_ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            ssl_ctx.check_hostname = check_hostname
            if not check_hostname:
                warnings.warn(
                    "TLS hostname verification is disabled for this MCP HTTP client.",
                    UserWarning,
                    stacklevel=2,
                )
            self.verify = ssl_ctx
        else:
            # If verify=False the cert/key files should not be specified
            if key_file or cert_file or ssl_ca_cert:
                raise ValueError(
                    "Either specify (`key_file`, `cert_file`, `ssl_ca_cert`) "
                    "or `verify=False`, not both."
                )
            self.verify = verify

        self.follow_redirects = follow_redirects

    def __call__(
        self,
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        # Set MCP defaults
        kwargs: dict[str, Any] = {
            "follow_redirects": self.follow_redirects,
            "verify": self.verify,
        }
        # Handle timeout
        if timeout is None:
            kwargs["timeout"] = httpx.Timeout(30.0)
        else:
            kwargs["timeout"] = timeout
        # Handle headers
        if headers is not None:
            kwargs["headers"] = headers
        # Handle authentication
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(**kwargs)
