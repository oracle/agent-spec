# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from pathlib import Path

import oracledb
import pytest
from agentspec_cts_sdk import AgentSpecRunnableComponent
from sqlalchemy import create_engine, text

from pyagentspec.property import FloatProperty, IntegerProperty, StringProperty
from pyagentspec.transforms import (
    ConversationSummarizationTransform as AgentSpecConversationSummarizationTransform,
)
from pyagentspec.transforms import (
    MessageSummarizationTransform as AgentSpecMessageSummarizationTransform,
)

VALID_CONFIGS_DIR = Path(__file__).parent / "valid_configs"
ORACLE_DATASTORE_NAME = "oracle"
POSTGRES_DATASTORE_NAME = "postgres"
IN_MEMORY_DATASTORE_NAME = "inmemory"


SCHEMA = {
    "message_summarization_cache": AgentSpecMessageSummarizationTransform.get_entity_definition(),
    "conversation_summarization_cache": AgentSpecConversationSummarizationTransform.get_entity_definition(),
}

MESSAGE_SUMMARIZATION_AGENT_FILE_PREFIX = "message_summarization_agent_"
CONVERSATION_SUMMARIZATION_AGENT_FILE_PREFIX = "conversation_summarization_agent_"


@pytest.fixture
def inmemory_datastore_for_summarization():
    return IN_MEMORY_DATASTORE_NAME, {}


@pytest.fixture(scope="session")
def oracle_database_connection():
    if not all(k in os.environ for k in ["ADB_DB_USER", "ADB_DB_PASSWORD", "ADB_DSN"]):
        pytest.skip("Oracle environment variables not set")
    conn = oracledb.connect(
        user=os.environ["ADB_DB_USER"],
        password=os.environ["ADB_DB_PASSWORD"],
        dsn=os.environ["ADB_DSN"],
    )
    try:
        yield conn
    finally:
        conn.close()


def create_entities_inside_oracle_database(oracle_database_connection):
    for collection_name, entity in SCHEMA.items():
        ddl = _get_ddl_for_entity(collection_name, entity)
        oracle_database_connection.cursor().execute(ddl)


def delete_entities_inside_oracle_database(oracle_database_connection):
    drop = [f"DROP TABLE IF EXISTS {entity_name}" for entity_name in SCHEMA.keys()]
    for stmt in drop:
        oracle_database_connection.cursor().execute(stmt)


def _get_ddl_for_entity(entity_name, entity):
    prop_lines = []
    for prop_name, prop_type in entity.properties.items():
        if isinstance(prop_type, StringProperty):
            sql_type = "VARCHAR(4000)"
        elif isinstance(prop_type, IntegerProperty):
            sql_type = "INTEGER"
        elif isinstance(prop_type, FloatProperty):
            sql_type = "DOUBLE PRECISION"
        else:
            sql_type = "VARCHAR2(4000)"  # fallback
        prop_lines.append(f"    {prop_name} {sql_type}")
    props_str = ",\n".join(prop_lines)
    create = f"CREATE TABLE {entity_name} (\n{props_str}\n)"
    return create


@pytest.fixture
def oracle_datastore_for_summarization(oracle_database_connection):
    sensitive_fields = {
        "oracle_config.user": os.environ["ADB_DB_USER"],
        "oracle_config.password": os.environ["ADB_DB_PASSWORD"],
        "oracle_config.dsn": os.environ["ADB_DSN"],
    }
    delete_entities_inside_oracle_database(oracle_database_connection)
    create_entities_inside_oracle_database(oracle_database_connection)
    try:
        yield ORACLE_DATASTORE_NAME, sensitive_fields
    finally:
        delete_entities_inside_oracle_database(oracle_database_connection)


@pytest.fixture(scope="session")
def postgres_database_connection():
    if not all(
        k in os.environ for k in ["POSTGRES_DB_USER", "POSTGRES_DB_PASSWORD", "POSTGRES_DB_URL"]
    ):
        pytest.skip("Postgres environment variables not set")
    engine = create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_DB_USER']}:{os.environ['POSTGRES_DB_PASSWORD']}@{os.environ['POSTGRES_DB_URL']}/postgres",
        connect_args={"sslmode": "disable"},
    )
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def create_entities_inside_postgres_database(postgres_database_connection):
    for collection_name, entity in SCHEMA.items():
        ddl = _get_ddl_for_entity(collection_name, entity)
        postgres_database_connection.execute(text(ddl))
        postgres_database_connection.commit()


def delete_entities_inside_postgres_database(postgres_database_connection):
    drop = [f"DROP TABLE IF EXISTS {entity_name}" for entity_name in SCHEMA.keys()]
    for stmt in drop:
        postgres_database_connection.execute(text(stmt))
        postgres_database_connection.commit()


@pytest.fixture
def postgres_datastore_for_summarization(postgres_database_connection):
    sensitive_fields = {
        "postgres_config.user": os.environ["POSTGRES_DB_USER"],
        "postgres_config.password": os.environ["POSTGRES_DB_PASSWORD"],
    }
    delete_entities_inside_postgres_database(postgres_database_connection)
    create_entities_inside_postgres_database(postgres_database_connection)
    try:
        yield POSTGRES_DATASTORE_NAME, sensitive_fields
    finally:
        delete_entities_inside_postgres_database(postgres_database_connection)


@pytest.fixture(
    params=[
        "inmemory_datastore_for_summarization",
        "oracle_datastore_for_summarization",
        "postgres_datastore_for_summarization",
    ]
)
def datastore(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def runnable_agent_with_message_summarization_transform_from_agentspec(
    datastore, load_agentspec_config
) -> AgentSpecRunnableComponent:
    datastore_name, datastore_sensitive_fields = datastore
    agent_yaml = (
        VALID_CONFIGS_DIR / f"{MESSAGE_SUMMARIZATION_AGENT_FILE_PREFIX}{datastore_name}.yaml"
    )
    yaml_content = agent_yaml.read_text()
    runtime_agent = load_agentspec_config(
        yaml_content, components_registry=datastore_sensitive_fields
    )
    return runtime_agent


@pytest.fixture
def runnable_agent_with_conversation_summarization_transform_from_agentspec(
    datastore,
    load_agentspec_config,
) -> AgentSpecRunnableComponent:
    datastore_name, datastore_sensitive_fields = datastore
    agent_yaml = (
        VALID_CONFIGS_DIR / f"{CONVERSATION_SUMMARIZATION_AGENT_FILE_PREFIX}{datastore_name}.yaml"
    )
    yaml_content = agent_yaml.read_text()
    runtime_agent = load_agentspec_config(
        yaml_content, components_registry=datastore_sensitive_fields
    )
    return runtime_agent
