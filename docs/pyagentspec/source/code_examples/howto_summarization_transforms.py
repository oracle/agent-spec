# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# .. define-llm-config
from pyagentspec.llms import OpenAiConfig

# Configure an LLM for summarization
llm_config = OpenAiConfig(
    id="summarization_llm",
    name="summarization_llm",
    model_id="gpt-4o-mini",
)

# .. start-transforms
from pyagentspec.transforms import ConversationSummarizationTransform, MessageSummarizationTransform

# Create a message summarization transform
message_summarizer = MessageSummarizationTransform(
    id="message_summarizer",
    name="message_summarizer",
    llm=llm_config,
    max_message_size=10_000,  # Summarize messages longer than 10k characters
    summarization_instructions="Create a concise summary of this message focusing on key points and actionable information.",
    summarized_message_template="Message summary: {{summary}}",
)

# Create a conversation summarization transform
conversation_summarizer = ConversationSummarizationTransform(
    id="conversation_summarizer",
    name="conversation_summarizer",
    llm=llm_config,
    max_num_messages=50,  # Summarize when conversation exceeds 50 messages
    min_num_messages=10,  # Keep the last 10 messages unsummarized
    summarization_instructions="Summarize this conversation thread, highlighting key decisions, action items, and important context.",
    summarized_conversation_template="Conversation summary: {{summary}}",
)
# .. end-transforms

# .. start-agent-with-transforms
from pyagentspec.agent import Agent

# Create an agent that uses both summarization transforms
agent_with_summarization = Agent(
    id="summarizing_agent",
    name="summarizing_agent",
    system_prompt="You are a helpful assistant that can handle long conversations and messages efficiently.",
    llm_config=llm_config,
    transforms=[message_summarizer, conversation_summarizer],
)
# .. end-agent-with-transforms

# .. start-serialization
from pyagentspec.serialization import AgentSpecSerializer

# Serialize the agent with transforms
serialized_agent = AgentSpecSerializer().to_yaml(agent_with_summarization)

print("\nSerialized Agent with Transforms:")
print(serialized_agent)
# .. end-serialization
