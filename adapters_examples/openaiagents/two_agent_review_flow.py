# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

from agents import Agent, ModelSettings, RunConfig, Runner, TResponseInputItem, trace
from openai.types.shared import Reasoning
from pydantic import BaseModel


class WorkflowInput(BaseModel):
    input_as_text: str


writer = Agent(
    name="Writer",
    instructions=(
        "Write a concise 3-bullet outline that addresses the user's request. "
        "Keep it under 60 words; only bullets."
    ),
    model="gpt-5.2",
    model_settings=ModelSettings(
        reasoning=Reasoning(effort="low"),
        verbosity="low",
    ),
)


reviewer = Agent(
    name="Reviewer",
    instructions=(
        "Review the outline for: completeness, clarity, and actionability. "
        "If any gap, propose one short improvement. Reply in <=50 words."
    ),
    model="gpt-4.1",
)


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Two-agent writer→reviewer"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": workflow["input_as_text"]},
                ],
            }
        ]

        w = await Runner.run(
            writer,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_two_agent_review",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in w.new_items])

        r = await Runner.run(
            reviewer,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_two_agent_review",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in r.new_items])

        return {"output_text": r.final_output_as(str)}


if __name__ == "__main__":
    import asyncio

    question = input("Task to outline and review: ")
    out = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))
    print("Result:", out)
