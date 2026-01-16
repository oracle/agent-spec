# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# .. define-schema
from pyagentspec.datastores import Entity
from pyagentspec.property import ObjectProperty, StringProperty

# Define a simple entity schema for a user profile collection
user_profile_entity: Entity = ObjectProperty(
    title="UserProfile",
    properties={
        "user_id": StringProperty(title="user_id"),
        "name": StringProperty(title="name"),
        "email": StringProperty(title="email"),
        "preferences": ObjectProperty(
            title="preferences",
            properties={
                "theme": StringProperty(title="theme"),
                "language": StringProperty(title="language"),
            },
        ),
    },
)

# Define schema for the datastore
from typing import Dict

datastore_schema: Dict[str, Entity] = {
    "user_profiles": user_profile_entity,
}

# .. start-oracle-tls
from pyagentspec.datastores.oracle import OracleDatabaseDatastore, TlsOracleDatabaseConnectionConfig

oracle_tls_config = TlsOracleDatabaseConnectionConfig(
    id="oracle_tls_config_id",
    name="oracle_tls_config",
    user="myuser",  # This field will not appear in serialized output
    password="mypassword",  # nosec  # This field will not appear in serialized output
    dsn="(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=myhost.example.com)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=myservice)))",  # This field will not appear in serialized output
    config_dir="/path/to/config/dir",
)

oracle_datastore = OracleDatabaseDatastore(
    name="oracle_datastore",
    datastore_schema=datastore_schema,
    connection_config=oracle_tls_config,
)
# .. end-oracle-tls

# .. start-oracle-mtls
from pyagentspec.datastores.oracle import MTlsOracleDatabaseConnectionConfig

oracle_mtls_config = MTlsOracleDatabaseConnectionConfig(
    id="oracle_mtls_config_id",
    name="oracle_mtls_config",
    user="myuser",  # This field will not appear in serialized output
    password="mypassword",  # nosec  # This field will not appear in serialized output
    dsn="(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=myhost.example.com)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=myservice)))",  # This field will not appear in serialized output
    config_dir="/path/to/config/dir",
    wallet_location="/path/to/wallet",
    wallet_password="mywalletpassword",  # nosec  # This field will not appear in serialized output
)

oracle_mtls_datastore = OracleDatabaseDatastore(
    name="oracle_mtls_datastore",
    datastore_schema=datastore_schema,
    connection_config=oracle_mtls_config,
)
# .. end-oracle-mtls

# .. start-postgres-tls
from pyagentspec.datastores.postgres import (
    PostgresDatabaseDatastore,
    TlsPostgresDatabaseConnectionConfig,
)

postgres_config = TlsPostgresDatabaseConnectionConfig(
    id="postgres_config_id",
    name="postgres_config",
    user="myuser",  # This field will not appear in serialized output
    password="mypassword",  # nosec  # This field will not appear in serialized output
    url="postgresql://myhost.example.com:5432/mydatabase",
    sslcert="/path/to/client.crt",
    sslkey="/path/to/client.key",  # This field will not appear in serialized output
    sslrootcert="/path/to/ca.crt",
    sslcrl="/path/to/crl.pem",
)

postgres_datastore = PostgresDatabaseDatastore(
    name="postgres_datastore",
    datastore_schema=datastore_schema,
    connection_config=postgres_config,
)
# .. end-postgres-tls

# .. start-in-memory
from pyagentspec.datastores import InMemoryCollectionDatastore

# For development, testing, or when persistent storage is not needed
in_memory_datastore = InMemoryCollectionDatastore(
    name="in_memory_datastore",
    datastore_schema=datastore_schema,
)
# .. end-in-memory

# .. start-serialization
from pyagentspec.serialization import AgentSpecSerializer

# Serialize any of the datastores
serialized_oracle = AgentSpecSerializer().to_json(oracle_datastore)
serialized_postgres = AgentSpecSerializer().to_json(postgres_datastore)
serialized_in_memory = AgentSpecSerializer().to_json(in_memory_datastore)

print("Oracle Datastore:")
print(serialized_oracle)
print("\nPostgreSQL Datastore:")
print(serialized_postgres)
print("\nIn-Memory Datastore:")
print(serialized_in_memory)
# .. end-serialization

# .. start-deserialization
from pyagentspec.serialization import AgentSpecDeserializer

# To deserialize configurations with sensitive fields, provide a components registry
# The keys are in the format "component_id.field"
components_registry = {
    "oracle_tls_config_id.user": "myuser",
    "oracle_tls_config_id.password": "mypassword",
    "oracle_tls_config_id.dsn": "(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=myhost.example.com)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=myservice)))",
    "postgres_config_id.user": "myuser",
    "postgres_config_id.password": "mypassword",
    "postgres_config_id.sslkey": "/path/to/client.key",
}

# Deserialize the configurations
deserializer = AgentSpecDeserializer()

deserialized_oracle = deserializer.from_json(
    json_content=serialized_oracle, components_registry=components_registry
)
deserialized_postgres = deserializer.from_json(
    json_content=serialized_postgres, components_registry=components_registry
)
# .. end-deserialization
