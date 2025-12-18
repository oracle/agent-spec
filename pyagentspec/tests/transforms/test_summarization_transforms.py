# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import pytest

from pyagentspec.llms import OpenAiConfig
from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer
from pyagentspec.transforms import ConversationSummarizationTransform, MessageSummarizationTransform

from ..test_datastores import (
    IN_MEMORY_SENSITIVE_FIELDS,
    ORACLE_MTLS_SENSITIVE_FIELDS,
    ORACLE_TLS_SENSITIVE_FIELDS,
    POSTGRES_TLS_SENSITIVE_FIELDS,
    SCHEMA,
    in_memory_datastore,
    oracle_datastore_mtls,
    oracle_datastore_tls,
    postgres_datastore_tls,
)


def create_test_llm_config():
    return OpenAiConfig(
        id="test_llm",
        name="test_openai_config",
        model_id="gpt-3.5-turbo",
    )


def create_message_summarization_transform(datastore):
    # Use non-default values to ensure serialization/deserialization preserves exact values
    return MessageSummarizationTransform(
        id="test_msg_summarizer",
        name="test_message_summarizer",
        llm=create_test_llm_config(),
        max_message_size=15_000,
        summarization_instructions=(
            "Create a concise summary of this message focusing on key points and actionable information."
        ),
        summarized_message_template="Message summary: {{summary}}",
        datastore=datastore,
        max_cache_size=2_500,
        max_cache_lifetime=8 * 3600,
        cache_collection_name="message_summaries_cache",
    )


def create_conversation_summarization_transform(datastore):
    # Use non-default values to ensure serialization/deserialization preserves exact values
    return ConversationSummarizationTransform(
        id="test_conv_summarizer",
        name="test_conversation_summarizer",
        llm=create_test_llm_config(),
        max_num_messages=75,
        min_num_messages=25,
        summarization_instructions=(
            "Summarize this conversation thread, highlighting key decisions, action items, and important context."
        ),
        summarized_conversation_template="Conversation summary: {{summary}}",
        datastore=datastore,
        max_cache_size=5_000,
        max_cache_lifetime=12 * 3600,
        cache_collection_name="conversation_summaries_cache",
    )


@pytest.mark.parametrize(
    "datastore_factory, sensitive_fields",
    [
        (in_memory_datastore, IN_MEMORY_SENSITIVE_FIELDS),
        (oracle_datastore_tls, ORACLE_TLS_SENSITIVE_FIELDS),
        (oracle_datastore_mtls, ORACLE_MTLS_SENSITIVE_FIELDS),
        (postgres_datastore_tls, POSTGRES_TLS_SENSITIVE_FIELDS),
    ],
)
@pytest.mark.parametrize(
    "transform_factory",
    [
        create_message_summarization_transform,
        create_conversation_summarization_transform,
    ],
)
def test_can_serialize_and_deserialize_transform_with_all_datastores(
    datastore_factory, sensitive_fields, transform_factory
):
    datastore = datastore_factory(SCHEMA)

    transform = transform_factory(datastore)

    serialized_transform = AgentSpecSerializer().to_yaml(transform)
    print(serialized_transform)
    assert len(serialized_transform.strip()) > 0

    deserialized_transform = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_transform, components_registry=sensitive_fields
    )
    assert deserialized_transform == transform

    serialized_transform = AgentSpecSerializer().to_json(transform)
    assert len(serialized_transform.strip()) > 0
    deserialized_transform = AgentSpecDeserializer().from_yaml(
        yaml_content=serialized_transform, components_registry=sensitive_fields
    )
    assert deserialized_transform == transform
