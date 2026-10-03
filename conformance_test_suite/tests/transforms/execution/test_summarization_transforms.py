# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict

import pytest

from ...conftest import DETERMINISTIC_LLM_CONF
from ..conftest import (
    CONVERSATION_SUMMARIZATION_AGENT_FILE_PREFIX,
    IN_MEMORY_DATASTORE_NAME,
    MESSAGE_SUMMARIZATION_AGENT_FILE_PREFIX,
    ORACLE_DATASTORE_NAME,
    POSTGRES_DATASTORE_NAME,
    SCHEMA,
    VALID_CONFIGS_DIR,
)

HELLO_WORLD = "Hello world!"
LONG_MESSAGE = HELLO_WORLD * 100

ACK_MESSAGE_IS_SUMMARIZED = "Thank you for the summarized message!"
ACK_CONVERSATION_IS_SUMMARIZED = "Thank you for the summarized conversation!"

MESSAGE_SUMMARIZATION_INSTRUCTIONS = "Please Summarize this message: "
CONVERSATION_SUMMARIZATION_INSTRUCTIONS = "Please Summarize this conversation: "

SUMMARIZED_MESSAGE_TEMPLATE = "Summarized message: {{summary}}"
SUMMARIZED_CONVERSATION_TEMPLATE = "Summarized conversation: {{summary}}"

MESSAGE_SUMMARIZATION_CACHE_COLLECTION_NAME = "message_summarization_cache"
CONVERSATION_SUMMARIZATION_CACHE_COLLECTION_NAME = "conversation_summarization_cache"

EXTRA_MESSAGE = "Message that makes the conversation too long."


@pytest.fixture
def prompt_regex_to_result_mappings() -> Dict[str, Any]:
    return {
        # ------ For MessageSummarizatonTransform ------
        # Long message --> Summarized Message
        f"{MESSAGE_SUMMARIZATION_INSTRUCTIONS}.*{HELLO_WORLD*40}.*": HELLO_WORLD,
        # Formatted Summarized Message --> ACK that agent llm received a summarized message
        SUMMARIZED_MESSAGE_TEMPLATE.replace("{{summary}}", HELLO_WORLD): ACK_MESSAGE_IS_SUMMARIZED,
        # ------ For ConversationSummarizationTransform ------
        # Conversation summary prompt --> summary
        f".*{CONVERSATION_SUMMARIZATION_INSTRUCTIONS}.*": HELLO_WORLD,
        # Formatted Summarized Conversation --> ACK
        ".*"
        + SUMMARIZED_CONVERSATION_TEMPLATE.replace("{{summary}}", HELLO_WORLD)
        + ".*"
        + EXTRA_MESSAGE: {
            "suffix_size": 2,  # matches the regex with the concatenation of last 2 messages.
            "value": ACK_CONVERSATION_IS_SUMMARIZED,
        },
        # For short conversations
        f"You are a helpful assistant.*{HELLO_WORLD}.*{HELLO_WORLD}.*{HELLO_WORLD}.*{HELLO_WORLD}.*{HELLO_WORLD}": "Short conversation not summarized",
    }


def test_messages_summarization_transforms_does_not_summarize_short_messages(
    runnable_agent_with_message_summarization_transform_from_agentspec,
    local_deterministic_llm_server,
) -> None:
    agent = runnable_agent_with_message_summarization_transform_from_agentspec
    agent.start()
    agent.append_user_message(HELLO_WORLD)
    agent.append_user_message(HELLO_WORLD)
    status = agent.run()

    last_message = status.agent_messages[-1]
    assert last_message != ACK_MESSAGE_IS_SUMMARIZED


def test_messages_summarization_transforms_summarizes_long_messages(
    runnable_agent_with_message_summarization_transform_from_agentspec,
    local_deterministic_llm_server,
) -> None:
    agent = runnable_agent_with_message_summarization_transform_from_agentspec
    agent.start()
    agent.append_user_message(LONG_MESSAGE)
    agent.append_user_message(LONG_MESSAGE)

    status = agent.run()

    last_message = status.agent_messages[-1]
    assert last_message == ACK_MESSAGE_IS_SUMMARIZED


def test_conversation_summarization_transforms_summarizes_long_conversations(
    runnable_agent_with_conversation_summarization_transform_from_agentspec,
    local_deterministic_llm_server,
) -> None:
    agent = runnable_agent_with_conversation_summarization_transform_from_agentspec
    agent.start()
    for _ in range(10):
        agent.append_user_message(HELLO_WORLD)
    agent.append_user_message(EXTRA_MESSAGE)

    status = agent.run()

    last_message = status.agent_messages[-1]
    assert last_message == ACK_CONVERSATION_IS_SUMMARIZED


def test_conversation_summarization_transforms_does_not_summarize_short_conversations(
    runnable_agent_with_conversation_summarization_transform_from_agentspec,
    local_deterministic_llm_server,
) -> None:
    agent = runnable_agent_with_conversation_summarization_transform_from_agentspec
    agent.start()
    for _ in range(5):
        agent.append_user_message(HELLO_WORLD)
    status = agent.run()

    last_message = status.agent_messages[-1]
    assert last_message != ACK_CONVERSATION_IS_SUMMARIZED


if __name__ == "__main__":
    # Run this file as a script to create the required .yaml configs that are needed to run the tests.
    from pyagentspec.agent import Agent as AgentSpecAgent
    from pyagentspec.datastores import InMemoryCollectionDatastore
    from pyagentspec.datastores.oracle import (
        OracleDatabaseDatastore as AgentSpecOracleDatabaseDatastore,
    )
    from pyagentspec.datastores.oracle import (
        TlsOracleDatabaseConnectionConfig as AgentSpecTlsOracleDatabaseConnectionConfig,
    )
    from pyagentspec.datastores.postgres import (
        PostgresDatabaseDatastore as AgentSpecPostgresDatabaseDatastore,
    )
    from pyagentspec.datastores.postgres import (
        TlsPostgresDatabaseConnectionConfig as AgentSpecTlsPostgresDatabaseConnectionConfig,
    )
    from pyagentspec.serialization import AgentSpecSerializer
    from pyagentspec.transforms import (
        ConversationSummarizationTransform as AgentSpecConversationSummarizationTransform,
    )
    from pyagentspec.transforms import (
        MessageSummarizationTransform as AgentSpecMessageSummarizationTransform,
    )

    inmemory_datastore = InMemoryCollectionDatastore(
        name="test-inmemory-datastore",
        datastore_schema=SCHEMA,
    )

    oracle_datastore = AgentSpecOracleDatabaseDatastore(
        id="oracle_ds",
        name="oracle_ds",
        datastore_schema=SCHEMA,
        connection_config=AgentSpecTlsOracleDatabaseConnectionConfig(
            id="oracle_config",
            name="oracle_config",
            user="sensitve-field-not-exported",
            password="sensitve-field-not-exported",
            dsn="sensitve-field-not-exported",  # nosec
        ),
    )

    import os

    postgres_datastore = AgentSpecPostgresDatabaseDatastore(
        id="postgres_ds",
        name="postgres_ds",
        datastore_schema=SCHEMA,
        connection_config=AgentSpecTlsPostgresDatabaseConnectionConfig(
            id="postgres_config",
            name="postgres_config",
            user="sensitve-field-not-exported",
            password="sensitve-field-not-exported",  # nosec
            url=os.environ.get("POSTGRES_DB_URL", "localhost:5432"),
            sslmode="disable",
        ),
    )

    datastores = [
        (IN_MEMORY_DATASTORE_NAME, inmemory_datastore),
        (ORACLE_DATASTORE_NAME, oracle_datastore),
        (POSTGRES_DATASTORE_NAME, postgres_datastore),
    ]

    # Create agents for each datastore
    for datastore_name, datastore in datastores:
        # Message summarization agent
        message_transform = AgentSpecMessageSummarizationTransform(
            name="message-summarizer",
            llm=DETERMINISTIC_LLM_CONF,
            datastore=datastore,
            max_message_size=100,
            cache_collection_name=MESSAGE_SUMMARIZATION_CACHE_COLLECTION_NAME,
            summarized_message_template=SUMMARIZED_MESSAGE_TEMPLATE,
            summarization_instructions=MESSAGE_SUMMARIZATION_INSTRUCTIONS,
        )
        message_agent = AgentSpecAgent(
            name="test-agent",
            system_prompt="You are a helpful assistant.",
            llm_config=DETERMINISTIC_LLM_CONF,
            transforms=[message_transform],
        )

        # Conversation summarization agent
        conversation_transform = AgentSpecConversationSummarizationTransform(
            name="conversation-summarizer",
            llm=DETERMINISTIC_LLM_CONF,
            datastore=datastore,
            max_num_messages=10,
            min_num_messages=1,
            cache_collection_name=CONVERSATION_SUMMARIZATION_CACHE_COLLECTION_NAME,
            summarization_instructions=CONVERSATION_SUMMARIZATION_INSTRUCTIONS,
            summarized_conversation_template=SUMMARIZED_CONVERSATION_TEMPLATE,
        )
        conversation_agent = AgentSpecAgent(
            name="test-agent",
            system_prompt="You are a helpful assistant.",
            llm_config=DETERMINISTIC_LLM_CONF,
            transforms=[conversation_transform],
        )

        message_yaml_path = (
            VALID_CONFIGS_DIR / f"{MESSAGE_SUMMARIZATION_AGENT_FILE_PREFIX}{datastore_name}.yaml"
        )
        conversation_yaml_path = (
            VALID_CONFIGS_DIR
            / f"{CONVERSATION_SUMMARIZATION_AGENT_FILE_PREFIX}{datastore_name}.yaml"
        )

        message_yaml_path.write_text(AgentSpecSerializer().to_yaml(message_agent))
        conversation_yaml_path.write_text(AgentSpecSerializer().to_yaml(conversation_agent))
