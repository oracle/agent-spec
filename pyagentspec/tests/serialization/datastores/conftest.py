# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.datastores import (
    InMemoryCollectionDatastore,
)
from pyagentspec.datastores.oracle import (
    MTlsOracleDatabaseConnectionConfig,
    OracleDatabaseDatastore,
    TlsOracleDatabaseConnectionConfig,
)
from pyagentspec.datastores.postgres import (
    PostgresDatabaseDatastore,
    TlsPostgresDatabaseConnectionConfig,
)
from pyagentspec.transforms import ConversationSummarizationTransform, MessageSummarizationTransform

FAKE_PASSWORD = "testpass"  # nosec B105
FAKE_TESTUSER = "testuser"
FAKE_DSN = "testdsn"

# Sensitive fields registries for different datastore types
ORACLE_TLS_SENSITIVE_FIELDS = {
    "myconfig.user": FAKE_TESTUSER,
    "myconfig.password": FAKE_PASSWORD,
    "myconfig.dsn": FAKE_DSN,
}

ORACLE_MTLS_SENSITIVE_FIELDS = {
    "myconfig_mtls.user": FAKE_TESTUSER,
    "myconfig_mtls.password": FAKE_PASSWORD,
    "myconfig_mtls.dsn": FAKE_DSN,
    "myconfig_mtls.wallet_location": "/wallet/location",
    "myconfig_mtls.wallet_password": "walletpass",
}

POSTGRES_TLS_SENSITIVE_FIELDS = {
    "myconfig_postgres.user": FAKE_TESTUSER,
    "myconfig_postgres.password": FAKE_PASSWORD,
    "myconfig_postgres.sslkey": "/path/to/client.key",
}

IN_MEMORY_SENSITIVE_FIELDS = {}

# Collection names (table names) for caching summarized messages and conversations.
TESTING_MESSAGES_COLLECTION = "collection1"
TESTING_CONVERSATIONS_COLLECTION = "collection2"

SCHEMA = {
    TESTING_MESSAGES_COLLECTION: MessageSummarizationTransform.get_entity_definition(),
    TESTING_CONVERSATIONS_COLLECTION: ConversationSummarizationTransform.get_entity_definition(),
}


def in_memory_datastore(schema):
    return InMemoryCollectionDatastore(name="our_inmem_ds", datastore_schema=schema)


def oracle_datastore_tls(schema):
    config = TlsOracleDatabaseConnectionConfig(
        id="myconfig",
        name="test_config",
        user=FAKE_TESTUSER,
        password=FAKE_PASSWORD,
        dsn=FAKE_DSN,
        protocol="tcps",
        config_dir="/configdir",
    )
    return OracleDatabaseDatastore(
        id="my_ds", name="oracle_ds", datastore_schema=schema, connection_config=config
    )


def oracle_datastore_mtls(schema):
    config = MTlsOracleDatabaseConnectionConfig(
        id="myconfig_mtls",
        name="test_config_mtls",
        user=FAKE_TESTUSER,
        password=FAKE_PASSWORD,
        dsn=FAKE_DSN,
        protocol="tcps",
        config_dir="/configdir",
        wallet_location="/wallet/location",
        wallet_password="walletpass",  # nosec B106
    )
    return OracleDatabaseDatastore(
        id="my_ds_mtls", name="oracle_ds_mtls", datastore_schema=schema, connection_config=config
    )


def postgres_datastore_tls(schema):
    config = TlsPostgresDatabaseConnectionConfig(
        id="myconfig_postgres",
        name="test_config_postgres",
        user=FAKE_TESTUSER,
        password=FAKE_PASSWORD,
        url="postgresql://localhost:5432/testdb",
        sslmode="require",
        sslcert="/path/to/client.crt",
        sslkey="/path/to/client.key",
        sslrootcert="/path/to/ca.crt",
    )
    return PostgresDatabaseDatastore(
        id="my_ds_postgres", name="postgres_ds", datastore_schema=schema, connection_config=config
    )


DATASTORES_AND_THEIR_SENSITIVE_FIELDS = [
    (in_memory_datastore(SCHEMA), IN_MEMORY_SENSITIVE_FIELDS),
    (oracle_datastore_tls(SCHEMA), ORACLE_TLS_SENSITIVE_FIELDS),
    (oracle_datastore_mtls(SCHEMA), ORACLE_MTLS_SENSITIVE_FIELDS),
    (postgres_datastore_tls(SCHEMA), POSTGRES_TLS_SENSITIVE_FIELDS),
]
