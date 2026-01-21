# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from agents import Agent, RunConfig, Runner, TResponseInputItem, function_tool, trace
from pydantic import BaseModel


# Distinct tool names to avoid hard-coding risks
@function_tool
def compute_glip(a: int, b: int) -> int:
    # glip = a**2 + 2ab + b**2
    return a * a + 2 * a * b + b * b


@function_tool
def compute_glap(a: int, b: int) -> int:
    # glap = a**3 + b**3
    return a * a * a + b * b * b


@function_tool
def compute_glop(a: int, b: int) -> int:
    # glop = a - b
    return a - b


class WorkflowInput(BaseModel):
    input_as_text: str


# One agent with three tools; model picks exactly one
tricoder = Agent(
    name="TriCoder",
    instructions="""
    You have three tools: compute_glip, compute_glap, compute_glop.\n
    - If the user mentions 'glip', call compute_glip with a and b.\n
    - If the user mentions 'glap', call compute_glap with a and b.\n
    - If the user mentions 'glop', call compute_glop with a and b.\n
    Extract integers a and b from the user text.\n
    Return only the numeric result as plain text.
    """,
    model="gpt-5-mini",
    tools=[compute_glip, compute_glap, compute_glop],
)


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Single agent with three tools"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": workflow["input_as_text"]},
                ],
            }
        ]

        result = await Runner.run(
            tricoder,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_single_agent_three_tools",
                }
            ),
        )

        conversation_history.extend([item.to_input_item() for item in result.new_items])

        return {"output_text": result.final_output_as(str)}


if __name__ == "__main__":
    import asyncio

    question = input("Your instruction (mention glip/glap/glop and numbers a,b): ")
    output = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))
    print(f"Result: {output}")
