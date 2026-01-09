# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""This file defines message transforms for message and conversation summarization."""
from typing import Optional, Union

from pydantic import Field, ValidationInfo, field_validator

from pyagentspec.datastores.datastore import Entity, InMemoryCollectionDatastore
from pyagentspec.datastores.oracle import OracleDatabaseDatastore
from pyagentspec.datastores.postgres import PostgresDatabaseDatastore
from pyagentspec.llms import LlmConfig
from pyagentspec.property import (
    FloatProperty,
    IntegerProperty,
    ObjectProperty,
    StringProperty,
    json_schema_is_castable_to,
)

from .transforms import MessageTransform

SupportedDatastores = Union[
    InMemoryCollectionDatastore, OracleDatabaseDatastore, PostgresDatabaseDatastore
]


def _validate_datastore_schema(
    provided_schema: dict[str, Entity], correct_schema: dict[str, Entity]
) -> None:
    # First check that all required collections are present
    for collection_name in correct_schema.keys():
        if collection_name not in provided_schema:
            raise ValueError(
                f"Datastore should contain collection {collection_name}. "
                f"Found {', '.join(provided_schema.keys())}"
            )

    for collection_name, correct_entity in correct_schema.items():
        provided_entity = provided_schema[collection_name]

        correct_props = correct_entity.json_schema.get("properties", {})
        provided_props = provided_entity.json_schema.get("properties", {})

        for prop_name, correct_prop_schema in correct_props.items():
            if prop_name not in provided_props:
                raise ValueError(
                    f"Collection {collection_name} should contain Entity {prop_name}. "
                    f"Found {', '.join(provided_props.keys())}"
                )

            provided_prop_schema = provided_props[prop_name]

            if not json_schema_is_castable_to(correct_prop_schema, provided_prop_schema):
                raise ValueError(
                    f"Entity: {prop_name} in collection {collection_name} has incompatible type. "
                    f"Expected: {correct_prop_schema}, Found: {provided_prop_schema}"
                )


def _get_default_inmemory_datastore_conversations() -> InMemoryCollectionDatastore:
    return InMemoryCollectionDatastore(
        name="default-inmemory-datastore",
        datastore_schema={
            "summarized_conversations_cache": ConversationSummarizationTransform.get_entity_definition()
        },
    )


def _get_default_inmemory_datastore_messages() -> InMemoryCollectionDatastore:
    return InMemoryCollectionDatastore(
        name="default-inmemory-datastore",
        datastore_schema={
            "summarized_messages_cache": MessageSummarizationTransform.get_entity_definition()
        },
    )


class MessageSummarizationTransform(MessageTransform):
    llm: LlmConfig
    """LLM configuration for summarization."""

    max_message_size: int = 20_000
    """Maximum message size in characters before triggering summarization."""

    summarization_instructions: str = (
        "Please make a summary of this message. Include relevant information and keep it short. "
        "Your response will replace the message, so just output the summary directly, no introduction needed."
    )
    """Instructions for the LLM on how to summarize messages."""

    summarized_message_template: str = "Summarized message: {{summary}}"
    """Template for formatting the summarized message output."""

    max_cache_size: Optional[int] = 10_000
    """Maximum number of cache entries to keep."""

    max_cache_lifetime: Optional[int] = 4 * 3600
    """Maximum lifetime of cache entries in seconds."""

    cache_collection_name: str = "summarized_messages_cache"
    """Name of the collection in the datastore for caching summarized messages."""

    datastore: Optional[SupportedDatastores] = Field(
        default_factory=_get_default_inmemory_datastore_messages
    )
    """
    Datastore on which to store the cache. By default, an in-memory datastore is created. If None, no caching will happen.
    """

    @staticmethod
    def get_entity_definition() -> Entity:
        return ObjectProperty(
            properties={
                "cache_key": StringProperty(),
                "cache_content": StringProperty(),
                "created_at": FloatProperty(),
                "last_used_at": FloatProperty(),
            }
        )

    @field_validator("datastore", mode="after")
    @classmethod
    def _validate_datastore(
        cls, value: Optional[SupportedDatastores], info: ValidationInfo
    ) -> Optional[SupportedDatastores]:
        if value is not None:
            cache_collection_name = info.data["cache_collection_name"]
            correct_schema = {cache_collection_name: cls.get_entity_definition()}
            _validate_datastore_schema(value.datastore_schema, correct_schema)
        return value


class ConversationSummarizationTransform(MessageTransform):
    llm: LlmConfig
    """LLM configuration for conversation summarization."""

    max_num_messages: int = 50
    """Maximum number of messages before triggering summarization."""

    min_num_messages: int = 10
    """Minimum number of recent messages to keep unsummarized."""

    summarization_instructions: str = (
        "Please make a summary of this conversation. Include relevant information and keep it short. "
        "Your response will replace the messages, so just output the summary directly, no introduction needed."
    )
    """Instructions for the LLM on how to summarize conversations."""

    summarized_conversation_template: str = "Summarized conversation: {{summary}}"
    """Template for formatting the summarized conversation output."""

    max_cache_size: Optional[int] = 10_000
    """Maximum number of cache entries to keep."""

    max_cache_lifetime: Optional[int] = 4 * 3600
    """Maximum lifetime of cache entries in seconds."""

    cache_collection_name: str = "summarized_conversations_cache"
    """Name of the collection in the datastore for caching summarized conversations."""

    datastore: Optional[SupportedDatastores] = Field(
        default_factory=_get_default_inmemory_datastore_conversations
    )
    """
    Datastore on which to store the cache. By default, an in-memory datastore is created. If None, no caching will happen.
    """

    @staticmethod
    def get_entity_definition() -> Entity:
        return ObjectProperty(
            properties={
                "cache_key": StringProperty(),
                "cache_content": StringProperty(),
                "prefix_size": IntegerProperty(),
                "created_at": FloatProperty(),
                "last_used_at": FloatProperty(),
            }
        )

    @field_validator("datastore", mode="after")
    @classmethod
    def _validate_datastore(
        cls, value: Optional[SupportedDatastores], info: ValidationInfo
    ) -> Optional[SupportedDatastores]:
        if value is not None:
            cache_collection_name = info.data["cache_collection_name"]
            correct_schema = {cache_collection_name: cls.get_entity_definition()}
            _validate_datastore_schema(value.datastore_schema, correct_schema)
        return value
