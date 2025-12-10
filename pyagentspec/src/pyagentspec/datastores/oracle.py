# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Literal, Optional

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField

from .datastore import RelationalDatastore


class OracleDatabaseConnectionConfig(Component, abstract=True):
    """Base class used for configuring connections to Oracle Database."""


class OracleDatabaseDatastore(RelationalDatastore):
    """Datastore that uses Oracle Database as the storage mechanism."""

    connection_config: OracleDatabaseConnectionConfig


class TlsOracleDatabaseConnectionConfig(OracleDatabaseConnectionConfig):
    """TLS Connection Configuration to Oracle Database."""

    user: SensitiveField[str]
    """User used to connect to the database"""

    password: SensitiveField[str]
    """Password for the provided user"""

    dsn: SensitiveField[str]
    """Connection string for the database (e.g., created using `oracledb.make_dsn`)"""

    config_dir: Optional[str] = None
    """Configuration directory for the database connection. Set this if you are using an
    alias from your tnsnames.ora files as a DSN. Make sure that the specified DSN is
    appropriate for TLS connections (as the tnsnames.ora file in a downloaded wallet
    will only include DSN entries for mTLS connections)"""

    protocol: Literal["tcp", "tcps"] = "tcps"
    """'tcp' or 'tcps' indicating whether to use unencrypted network traffic or encrypted network traffic (TLS)"""


class MTlsOracleDatabaseConnectionConfig(TlsOracleDatabaseConnectionConfig):
    """Mutual-TLS Connection Configuration to Oracle Database."""

    wallet_location: SensitiveField[str]
    """Location where the Oracle Database wallet is stored."""

    wallet_password: SensitiveField[str]
    """Password for the provided wallet."""
