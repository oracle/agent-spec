# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from agents import Agent, RunConfig, Runner, TResponseInputItem, function_tool, trace
from pydantic import BaseModel


# Tool definitions
@function_tool
def calculate_zwak_function(a: int, b: int) -> int:
    return a * b - a - b


@function_tool
def calculate_zwik_function(a: int, b: int) -> int:
    return a**2 + b**2


@function_tool
def calculate_zwok_function(a: int, b: int) -> int:
    return a * b + a + b


class RouterSchema(BaseModel):
    classification: str


router = Agent(
    name="Router",
    instructions="""You are a classifier.

  You must classify if the user is looking to calculate the "zwik", "zwak" or "zwok" functions. If none of those apply, output "other".

  Say nothing else.
""",
    model="gpt-5-mini",
    output_type=RouterSchema,
)


calculate_zwik_function = Agent(
    name="Zwik",
    instructions="You have a calculate_zwik_function tool.",
    model="gpt-5-mini",
    tools=[calculate_zwik_function],
)


calculate_zwak_function = Agent(
    name="Zwak",
    instructions="You have a calculate_zwak_function tool.",
    model="gpt-5-mini",
    tools=[calculate_zwak_function],
)


calculate_zwok_function = Agent(
    name="Zwok",
    instructions="You have a calculate_zwok_function tool.",
    model="gpt-5-mini",
    tools=[calculate_zwok_function],
)


fail = Agent(
    name="Fail",
    instructions="Inform the user that an unresolvable error (code 778877) has occurred ",
    model="gpt-5-mini",
)


class WorkflowInput(BaseModel):
    input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
    with trace("Router math flow"):
        state = {}
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {"role": "user", "content": [{"type": "input_text", "text": workflow["input_as_text"]}]}
        ]
        router_result_temp = await Runner.run(
            router,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_68fa8aa9c674819091702dc46943365e0cabaf2d665967e4",
                }
            ),
        )

        conversation_history.extend([item.to_input_item() for item in router_result_temp.new_items])

        router_result = {
            "output_text": router_result_temp.final_output.model_dump_json(),
            "output_parsed": router_result_temp.final_output.model_dump(),
        }
        if router_result["output_parsed"]["classification"] == "zwik":
            zwik_result_temp = await Runner.run(
                calculate_zwik_function,
                input=[*conversation_history],
                run_config=RunConfig(
                    trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "wf_68fa8aa9c674819091702dc46943365e0cabaf2d665967e4",
                    }
                ),
            )

            conversation_history.extend(
                [item.to_input_item() for item in zwik_result_temp.new_items]
            )

            zwik_result = {"output_text": zwik_result_temp.final_output_as(str)}
            return zwik_result
        elif router_result["output_parsed"]["classification"] == "zwak":
            zwak_result_temp = await Runner.run(
                calculate_zwak_function,
                input=[*conversation_history],
                run_config=RunConfig(
                    trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "wf_68fa8aa9c674819091702dc46943365e0cabaf2d665967e4",
                    }
                ),
            )

            conversation_history.extend(
                [item.to_input_item() for item in zwak_result_temp.new_items]
            )

            zwak_result = {"output_text": zwak_result_temp.final_output_as(str)}
            return zwak_result
        elif router_result["output_parsed"]["classification"] == "zwok":
            zwok_result_temp = await Runner.run(
                calculate_zwok_function,
                input=[*conversation_history],
                run_config=RunConfig(
                    trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "wf_68fa8aa9c674819091702dc46943365e0cabaf2d665967e4",
                    }
                ),
            )

            conversation_history.extend(
                [item.to_input_item() for item in zwok_result_temp.new_items]
            )

            zwok_result = {"output_text": zwok_result_temp.final_output_as(str)}
            return zwok_result
        else:
            fail_result_temp = await Runner.run(
                fail,
                input=[*conversation_history],
                run_config=RunConfig(
                    trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "wf_68fa8aa9c674819091702dc46943365e0cabaf2d665967e4",
                    }
                ),
            )

            conversation_history.extend(
                [item.to_input_item() for item in fail_result_temp.new_items]
            )

            fail_result = {"output_text": fail_result_temp.final_output_as(str)}
            return fail_result


if __name__ == "__main__":
    import asyncio

    question = input("Your question: ")

    workflow_input = WorkflowInput(input_as_text=question)

    output = asyncio.run(run_workflow(workflow_input))

    print(f"Result: {output}")
