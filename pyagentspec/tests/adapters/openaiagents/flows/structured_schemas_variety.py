# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Literal

from agents import Agent, RunConfig, Runner, TResponseInputItem, trace
from pydantic import BaseModel


class Extraction(BaseModel):
    title: str
    priority: int
    urgent: bool


class SentimentLabel(BaseModel):
    label: Literal["positive", "negative", "neutral"]


class SummaryQuality(BaseModel):
    summary: str
    quality: Literal["low", "medium", "high"]


class WorkflowInput(BaseModel):
    input_as_text: str


extractor = Agent(
    name="Extractor",
    instructions=(
        "Extract a title, priority (as integer), and whether it's urgent (true/false). "
        "Return only structured fields."
    ),
    model="gpt-5-mini",
    output_type=Extraction,
)


classifier = Agent(
    name="Sentiment",
    instructions=(
        "Classify sentiment label strictly as one of: 'positive', 'negative', or 'neutral'. "
        "Return only the label."
    ),
    model="gpt-5-mini",
    output_type=SentimentLabel,
)


summarizer = Agent(
    name="Summarizer",
    instructions=(
        "Summarize the text and assign a quality rating as one of: 'low', 'medium', 'high'. "
        "Return only summary and quality."
    ),
    model="gpt-4o-mini",
    output_type=SummaryQuality,
)


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Structured schemas variety"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": workflow["input_as_text"]},
                ],
            }
        ]

        # Run extractor
        ex = await Runner.run(
            extractor,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_structured_schemas_variety",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in ex.new_items])

        # Run sentiment classifier
        cl = await Runner.run(
            classifier,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_structured_schemas_variety",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in cl.new_items])

        # Run summarizer with quality enum
        su = await Runner.run(
            summarizer,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_structured_schemas_variety",
                }
            ),
        )
        conversation_history.extend([item.to_input_item() for item in su.new_items])

        return {"output_text": su.final_output_as(str)}


if __name__ == "__main__":
    import asyncio

    question = input("Your text: ")
    output = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))
    print(f"Result: {output}")
