# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Callable, Iterable, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow

# ---------- Helpers ----------


def make_agent(
    name: str,
    model_client,
    system_message: str,
    description: Optional[str] = "",
) -> AssistantAgent:
    # Ensure we always pass a real str to AssistantAgent (mypy + runtime safe)
    safe_description: str = description if description is not None else ""
    return AssistantAgent(
        name=name,
        model_client=model_client,
        system_message=system_message,
        description=safe_description,
    )


def build_flow(
    participants: Iterable[AssistantAgent],
    build_graph_fn: Callable[[DiGraphBuilder], None],
    entry_point: Optional[AssistantAgent] = None,
    termination_condition: Optional[MaxMessageTermination] = None,
) -> GraphFlow:
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


# Shared builders for specific patterns


def build_basic_conditional_branch_flow(model_client, use_lambda: bool, termination_condition):
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer in [1,3]. Only say the number you generate without any extra text.",
    )
    one_agent = make_agent(
        "one_agent",
        model_client,
        "Without adding extra text or reformatting, say exactly the following text: 'Number 1 generated.'",
    )
    two_agent = make_agent(
        "two_agent",
        model_client,
        "Without adding extra text or reformatting, say exactly the following text: 'Number 2 generated.'",
    )

    def build_graph_fn(b: DiGraphBuilder):
        if use_lambda:
            b.add_edge(generator, two_agent, condition=lambda msg: "2" in msg.to_model_text())
            b.add_edge(generator, one_agent, condition=lambda msg: "1" in msg.to_model_text())
        else:
            b.add_edge(generator, two_agent, condition="2")
            b.add_edge(generator, one_agent, condition="1")

    flow = build_flow(
        [generator, one_agent, two_agent],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow, ["generator"]


def build_simple_conditional_branch_flow(model_client, use_lambda: bool, termination_condition):
    # Same as “simple” test: generator -> reviewer -> {finish|continue}
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer between 1 and 4. Only say the number you generate without extra text.",
    )
    reviewer = make_agent(
        "reviewer",
        model_client,
        "write 'FINISH' if number is 2. Otherwise say 'CONTINUE'. Do not add extra text.",
    )
    finish_agent = make_agent(
        "finish_agent",
        model_client,
        "Say 'GAME FINISHED.'. Do not add extra text.",
    )
    continue_agent = make_agent(
        "continue_agent",
        model_client,
        "Say 'GAME CONTINUES...'. Do not add extra text.",
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(generator, reviewer)
        if use_lambda:
            b.add_edge(
                reviewer, finish_agent, condition=lambda msg: "FINISH" in msg.to_model_text()
            )
            b.add_edge(
                reviewer, continue_agent, condition=lambda msg: "CONTINUE" in msg.to_model_text()
            )
        else:
            b.add_edge(reviewer, finish_agent, condition="FINISH")
            b.add_edge(reviewer, continue_agent, condition="CONTINUE")

    flow = build_flow(
        [generator, reviewer, finish_agent, continue_agent],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow, ["reviewer"]


def build_simple_conditional_loop_two_end_nodes_flow(
    model_client, use_lambda: bool, termination_condition
):
    # Loop with 2 terminating branches and a loop-back path
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer between 1 and 6. Only say the number you generate without extra text.",
    )
    reviewer = make_agent(
        "reviewer",
        model_client,
        "write 'FINISH' if number is 2 and 'BLACK_HOLE' if number is 3. Otherwise say 'CONTINUE'. Do not add extra text.",
    )
    finish_agent = make_agent(
        "finish_agent",
        model_client,
        "Say 'GAME FINISHED.'. Do not add extra text.",
    )
    black_hole_agent = make_agent(
        "black_hole_agent",
        model_client,
        "Say 'You are in a black hole.'. Do not add extra text.",
    )
    continue_agent = make_agent(
        "continue_agent",
        model_client,
        "Say 'GAME CONTINUES...'. Do not add extra text.",
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(generator, reviewer)
        if use_lambda:
            b.add_edge(
                reviewer, finish_agent, condition=lambda msg: "FINISH" in msg.to_model_text()
            )
            b.add_edge(
                reviewer, continue_agent, condition=lambda msg: "FINISH" not in msg.to_model_text()
            )
            b.add_edge(
                reviewer,
                black_hole_agent,
                condition=lambda msg: "BLACK_HOLE" in msg.to_model_text(),
            )
        else:
            b.add_edge(reviewer, finish_agent, condition="FINISH")
            b.add_edge(reviewer, continue_agent, condition="CONTINUE")
            b.add_edge(reviewer, black_hole_agent, condition="BLACK_HOLE")
        b.add_edge(continue_agent, generator)

    flow = build_flow(
        [generator, reviewer, finish_agent, continue_agent, black_hole_agent],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow, ["reviewer"]


def build_simple_conditional_loop_flow(model_client, use_lambda: bool, termination_condition):
    # Loop with single terminator and loop-back path
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer between 1 and 6. Only say the number you generate without extra text.",
    )
    reviewer = make_agent(
        "reviewer",
        model_client,
        "write 'FINISH' if number is 2. Otherwise say 'CONTINUE'. Do not add extra text.",
    )
    finish_agent = make_agent(
        "finish_agent",
        model_client,
        "Say 'GAME FINISHED.'. Do not add extra text.",
    )
    continue_agent = make_agent(
        "continue_agent",
        model_client,
        "Say 'GAME CONTINUES...'. Do not add extra text.",
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(generator, reviewer)
        if use_lambda:
            b.add_edge(
                reviewer, finish_agent, condition=lambda msg: "FINISH" in msg.to_model_text()
            )
            b.add_edge(
                reviewer, continue_agent, condition=lambda msg: "FINISH" not in msg.to_model_text()
            )
        else:
            b.add_edge(reviewer, finish_agent, condition="FINISH")
            b.add_edge(reviewer, continue_agent, condition="CONTINUE")
        b.add_edge(continue_agent, generator)

    flow = build_flow(
        [generator, reviewer, finish_agent, continue_agent],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow, ["reviewer"]


def build_multiple_conditional_branches_flow(model_client, use_lambda: bool, termination_condition):
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer in [1,5). Only say the number you generate without any extra text.",
    )
    odd_number_agent = make_agent("odd_number_agent", model_client, "Say: 'Odd number generated.'")
    even_number_agent = make_agent(
        "even_number_agent", model_client, "Say: 'Even number generated.'"
    )
    one_agent = make_agent("one_agent", model_client, "Say: 'Number 1 generated.'")
    two_agent = make_agent("two_agent", model_client, "Say: 'Number 2 generated.'")
    three_agent = make_agent("three_agent", model_client, "Say: 'Number 3 generated.'")
    four_agent = make_agent("four_agent", model_client, "Say: 'Number 4 generated.'")

    def build_graph_fn(b: DiGraphBuilder):
        if use_lambda:
            # Split to odd/even via lambda checks, then route to specific number agents via lambda
            b.add_edge(
                generator,
                odd_number_agent,
                condition=lambda msg: any(d in (t := msg.to_model_text()) for d in ("1", "3")),
            )
            b.add_edge(
                generator,
                even_number_agent,
                condition=lambda msg: any(d in (t := msg.to_model_text()) for d in ("2", "4")),
            )
            b.add_edge(
                odd_number_agent, one_agent, condition=lambda msg: "1" in msg.to_model_text()
            )
            b.add_edge(
                even_number_agent, two_agent, condition=lambda msg: "2" in msg.to_model_text()
            )
            b.add_edge(
                odd_number_agent, three_agent, condition=lambda msg: "3" in msg.to_model_text()
            )
            b.add_edge(
                even_number_agent, four_agent, condition=lambda msg: "4" in msg.to_model_text()
            )
        else:
            # String-conditions variant:
            # Route generator -> odd/even with multiple string conditions
            b.add_edge(generator, odd_number_agent, condition="1")
            b.add_edge(generator, odd_number_agent, condition="3")
            b.add_edge(generator, even_number_agent, condition="2")
            b.add_edge(generator, even_number_agent, condition="4")
            # Then route to specific number agents using string conditions
            b.add_edge(odd_number_agent, one_agent, condition="1")
            b.add_edge(even_number_agent, two_agent, condition="2")
            b.add_edge(odd_number_agent, three_agent, condition="3")
            b.add_edge(even_number_agent, four_agent, condition="4")

    flow = build_flow(
        [
            generator,
            odd_number_agent,
            even_number_agent,
            one_agent,
            two_agent,
            three_agent,
            four_agent,
        ],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    # The inspector expects branch nodes for generator, even_number_agent, odd_number_agent
    return flow, ["generator", "even_number_agent", "odd_number_agent"]


def build_basic_conditional_branch_without_loop_flow_mix_string_and_lambda_conditions(
    model_client, termination_condition
):
    generator = make_agent(
        "generator",
        model_client,
        "Generate a random integer in [1,4]. Only say the number you generate without any extra text.",
    )
    one_agent = make_agent(
        "one_agent",
        model_client,
        "Without adding extra text or reformatting, say exactly the following text: 'one_agent reached.'",
    )
    two_agent = make_agent(
        "two_agent",
        model_client,
        "Without adding extra text or reformatting, say exactly the following text: 'two_agent reached.'",
    )
    default_agent = make_agent(
        "default_agent",
        model_client,
        "Without adding extra text or reformatting, say exactly the following text: 'Default agent reached'",
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(generator, two_agent, condition="2")
        b.add_edge(generator, one_agent, condition="1")
        b.add_edge(
            generator,
            default_agent,
            condition=lambda msg: "1" not in msg.to_model_text() and "2" not in msg.to_model_text(),
        )

    flow = build_flow(
        [generator, one_agent, two_agent, default_agent],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow


def build_conditional_loop_flow_lambda_condition(model_client, termination_condition):
    generator = make_agent("generator", model_client, "Generate a list of creative ideas.")
    reviewer = make_agent(
        "reviewer",
        model_client,
        "Review ideas and provide feedbacks, or just 'APPROVE' for final approval.",
    )
    summarizer = make_agent(
        "summary", model_client, "Summarize the user request and the final feedback."
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(generator, reviewer)
        b.add_edge(reviewer, summarizer, condition=lambda msg: "APPROVE" in msg.to_model_text())
        b.add_edge(reviewer, generator, condition=lambda msg: "APPROVE" not in msg.to_model_text())

    flow = build_flow(
        [generator, reviewer, summarizer],
        build_graph_fn,
        entry_point=generator,
        termination_condition=termination_condition,
    )
    return flow


def build_parallel_agents_flow(model_client):
    writer = make_agent("writer", model_client, "Draft a short paragraph on climate change.")
    editor1 = make_agent("editor1", model_client, "Edit the paragraph for grammar.")
    editor2 = make_agent("editor2", model_client, "Edit the paragraph for style.")
    final_reviewer = make_agent(
        "final_reviewer",
        model_client,
        "Consolidate the grammar and style edits into a final version.",
    )

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(writer, editor1)
        b.add_edge(writer, editor2)
        b.add_edge(editor1, final_reviewer)
        b.add_edge(editor2, final_reviewer)

    flow = build_flow([writer, editor1, editor2, final_reviewer], build_graph_fn)
    return flow


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

    def build_graph_fn(b: DiGraphBuilder):
        b.add_edge(writer, reviewer)

    flow = build_flow([writer, reviewer], build_graph_fn)
    return flow
