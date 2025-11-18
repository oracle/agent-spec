# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


# mypy: ignore-errors

import asyncio
import sys
from pathlib import Path

from autogen_agentchat.ui import Console
from autogen_ext.models.ollama import OllamaChatCompletionClient
from wayflowcore.agentspec import AgentSpecLoader

from autogen_agentspec_adapter import AgentSpecExporter

# Add repository root (parent of examples) to sys.path so that `import tests...` works
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.model_builders import build_sequential_agents_flow


def test_sequential_flow() -> None:

    model_client = OllamaChatCompletionClient(
        model="llama3.2:latest",
        host="localhost:11434",
    )

    flow = build_sequential_agents_flow(model_client)

    # 1) Test AutoGen

    async def run_sequential_flow() -> None:
        # Run the workflow
        await Console(flow.run_stream(task="Write a short paragraph about climate change."))

    asyncio.run(run_sequential_flow())

    # 2) Test WayFlow

    exporter = AgentSpecExporter()

    agentspec_yaml = exporter.to_yaml(flow)

    loader = AgentSpecLoader()

    assistant_flow = loader.load_yaml(agentspec_yaml)

    # Execute the flow
    conversation = assistant_flow.start_conversation()
    conversation.execute()

    conversation.append_user_message("Write a short paragraph about climate change.")
    conversation.execute()

    print("# Print all messages:")
    for message in conversation.message_list.get_messages()[::-1]:
        print(message)

    print("# Conversation span")
    from wayflowcore.tracing.span import ConversationSpan

    # Execute the flow
    conversation = assistant_flow.start_conversation()
    conversation.execute()
    conversation.append_user_message("Write a short paragraph about climate change.")
    with ConversationSpan(conversation=conversation) as conversation_span:
        status = conversation.execute()
        print(conversation)
        conversation_span.record_end_span_event(status)


test_sequential_flow()
