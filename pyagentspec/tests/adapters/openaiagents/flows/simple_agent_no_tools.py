# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from agents import Agent, RunConfig, Runner, TResponseInputItem, trace
from pydantic import BaseModel


class WorkflowInput(BaseModel):
    input_as_text: str


# A minimal flow: just one agent, no tools, no output schema
simple_echo = Agent(
    name="SimpleEcho",
    instructions="Return the user input text exactly. Say nothing else.",
    model="gpt-5-mini",
)


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Simple agent (no tools)"):
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
            simple_echo,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_simple_agent_no_tools",
                }
            ),
        )

        conversation_history.extend([item.to_input_item() for item in result.new_items])

        return {"output_text": result.final_output_as(str)}


if __name__ == "__main__":
    import asyncio

    question = input("Your text: ")
    output = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))
    print(f"Result: {output}")
