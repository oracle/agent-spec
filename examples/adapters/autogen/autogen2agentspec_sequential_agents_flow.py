# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import asyncio
from typing import Callable, Iterable, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
from wayflowcore.agentspec import AgentSpecLoader

from pyagentspec.adapters.autogen import AgentSpecExporter


def build_flow(
    participants: Iterable["AssistantAgent"],
    build_graph_fn: Callable[["DiGraphBuilder"], None],
    entry_point: Optional["AssistantAgent"] = None,
    termination_condition: Optional["MaxMessageTermination"] = None,
) -> "GraphFlow":
    from autogen_agentchat.teams import DiGraphBuilder, GraphFlow

    builder = DiGraphBuilder()
    for p in participants:
        builder.add_node(p)
    build_graph_fn(builder)
    if entry_point is not None:
        builder.set_entry_point(entry_point)
    graph = builder.build()
    return GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
        termination_condition=termination_condition,
    )


def make_agent(
    name: str,
    model_client,
    system_message: str,
    description: Optional[str] = "",
) -> "AssistantAgent":
    from autogen_agentchat.agents import AssistantAgent

    # Ensure we always pass a real str to AssistantAgent (mypy + runtime safe)
    safe_description: str = description if description is not None else ""
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=system_message,
        description=safe_description,
    )


def build_sequential_agents_flow(model_client):
    writer = make_agent(
        "writer",
        model_client,
        "Draft a short paragraph on climate change.",
        description="writer agent",
    )
    reviewer = make_agent(
        "reviewer",
        model_client,
        "Review the draft and suggest improvements.",
        description="reviewer agent",
    )

    def build_graph_fn(b: "DiGraphBuilder"):
        b.add_edge(writer, reviewer)

    flow = build_flow([writer, reviewer], build_graph_fn)
    return flow


def test_sequential_flow() -> None:

    model_client = OpenAIChatCompletionClient(
        model="/storage/models/Llama-3.3-70B-Instruct",
        base_url="http://url.to.my.llm/v1",
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family=ModelFamily.LLAMA_3_3_70B,
            structured_output=True,
        ),
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
