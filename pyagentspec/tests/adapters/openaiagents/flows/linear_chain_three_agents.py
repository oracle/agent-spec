# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from agents import Agent, RunConfig, Runner, TResponseInputItem, trace
from pydantic import BaseModel


class NormalizedInput(BaseModel):
    text: str


class Classification(BaseModel):
    intent: str


class WorkflowInput(BaseModel):
    input_as_text: str


normalizer = Agent(
    name="Normalizer",
    instructions=(
        "Lowercase the user's text and remove leading/trailing whitespace."
        "Return only the normalized text."
    ),
    model="gpt-5-mini",
    output_type=NormalizedInput,
)


classifier = Agent(
    name="Classifier",
    instructions=(
        "Classify the user's intent as one of: 'question', 'command', or 'other'."
        "Return only the label."
    ),
    model="gpt-4o-mini",  # vary model choice
    output_type=Classification,
)


responder = Agent(
    name="Responder",
    instructions=(
        "If intent is 'question', reply with 'Q'. If 'command', reply with 'C'. Else reply 'O'."
        "Return only that single character."
    ),
    model="gpt-5-mini",
)


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Linear chain A->B->C"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": workflow["input_as_text"]},
                ],
            }
        ]

        n = await Runner.run(
            normalizer,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_linear_chain",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in n.new_items])

        c = await Runner.run(
            classifier,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_linear_chain",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in c.new_items])

        r = await Runner.run(
            responder,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_linear_chain",
                }
            ),
        )

        conversation_history.extend([item.to_input_item() for item in r.new_items])

        return {"output_text": r.final_output_as(str)}


if __name__ == "__main__":
    import asyncio

    question = input("Your text: ")
    output = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))
    print(f"Result: {output}")
