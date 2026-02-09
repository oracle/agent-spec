# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import asyncio

from autogen_core.models import ModelFamily

from pyagentspec.adapters.autogen import AgentSpecLoader
from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import FloatProperty
from pyagentspec.tools import ClientTool, ServerTool

addition_tool = ClientTool(
    name="addition-tool",
    description="adds two numbers together",
    inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
    outputs=[FloatProperty(title="sum")],
)

subtraction_tool = ServerTool(
    name="subtraction-tool",
    description="subtract two numbers together",
    inputs=[FloatProperty(title="a"), FloatProperty(title="b")],
    outputs=[FloatProperty(title="difference")],
)

agentspec_llm_config = VllmConfig(
    name="llama-3.3-70b-instruct",
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    url="http://url.to.my.llm/v1",
    metadata={
        "model_info": {
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": ModelFamily.LLAMA_3_3_70B,
            "structured_output": True,
        }
    },
)

agentspec = Agent(
    id="1",
    name="agentspec_tools_test",
    description="agentspec_tools_test",
    llm_config=agentspec_llm_config,
    system_prompt="Perform sum and subtraction with the given tools.",
    tools=[addition_tool, subtraction_tool],
)


def subtract(a: float, b: float) -> float:
    return a - b


async def main() -> None:
    converter = AgentSpecLoader(tool_registry={"subtraction-tool": subtract})
    component = converter.load_component(agentspec)
    while True:
        input_cmd = input("USER >> ")
        if input_cmd == "q":
            break
        result = await component.run(task=input_cmd)
        print(result.messages[-1].content)
    await component._model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
