# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""This file defines message transforms for message and conversation summarization."""
from typing import Optional

from pyagentspec.datastores import Datastore
from pyagentspec.llms import LlmConfig

from .transforms import MessageTransform


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

    datastore: Optional[Datastore] = None
    """
    Datastore on which to store the cache. If None, an in-memory Datastore will be created automatically.
    """

    max_cache_size: Optional[int] = 10_000
    """Maximum number of cache entries to keep."""

    max_cache_lifetime: Optional[int] = 4 * 3600
    """Maximum lifetime of cache entries in seconds."""

    cache_collection_name: str = "summarized_messages_cache"
    """Name of the collection in the datastore for caching summarized messages."""


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

    datastore: Optional[Datastore] = None
    """
    Datastore on which to store the cache. If None, an in-memory Datastore will be created automatically.
    """

    max_cache_size: Optional[int] = 10_000
    """Maximum number of cache entries to keep."""

    max_cache_lifetime: Optional[int] = 4 * 3600
    """Maximum lifetime of cache entries in seconds."""

    cache_collection_name: str = "summarized_conversations_cache"
    """Name of the collection in the datastore for caching summarized conversations."""
