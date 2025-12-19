# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""This module defines the postgres datastore and postgres database connnection configuration components."""

from typing import Literal, Optional

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField

from .datastore import RelationalDatastore


class PostgresDatabaseConnectionConfig(Component, abstract=True):
    """Base class for a PostgreSQL connection."""


class PostgresDatabaseDatastore(RelationalDatastore):
    """Datastore that uses PostgreSQL Database as the storage mechanism."""

    connection_config: PostgresDatabaseConnectionConfig


class TlsPostgresDatabaseConnectionConfig(PostgresDatabaseConnectionConfig):
    """Configuration for a PostgreSQL connection with TLS/SSL support."""

    user: SensitiveField[str]
    """User of the postgres database"""

    password: SensitiveField[str]
    """Password of the postgres database"""

    url: str
    """URL to access the postgres database"""

    sslmode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = (
        "require"
    )
    """SSL mode for the PostgreSQL connection."""

    sslcert: Optional[str] = None
    """Path of the client SSL certificate, replacing the default `~/.postgresql/postgresql.crt`.
    Ignored if an SSL connection is not made."""

    sslkey: Optional[SensitiveField[str]] = None
    """Path of the file containing the secret key used for the client certificate, replacing the default
    `~/.postgresql/postgresql.key`. Ignored if an SSL connection is not made."""

    sslrootcert: Optional[str] = None
    """Path of the file containing SSL certificate authority (CA) certificate(s). Used to verify server identity."""

    sslcrl: Optional[str] = None
    """Path of the SSL server certificate revocation list (CRL). Certificates listed will be rejected
    while attempting to authenticate the server's certificate."""
