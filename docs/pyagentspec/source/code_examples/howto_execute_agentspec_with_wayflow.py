# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

# OciClientConfigWithUserAuthentication removed from PyAgentSpec
# but not in wayflowcore
exit()

# .. start-full-code
import logging
import warnings

from wayflowcore import MessageType
from wayflowcore.agentspec import AgentSpecLoader
from wayflowcore.tools import ServerTool

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)

AGENTSPEC_CONFIG = """
component_type: Agent
id: e52d2c57-0bdc-4f25-948a-2e9d9f670008
name: Math homework assistant
description: null
metadata: {}
inputs: []
outputs: []
llm_config:
  component_type: VllmConfig
  id: vllm_config
  name: llama-3.1-8b-instruct
  description: null
  metadata: {}
  default_generation_parameters: {}
  url: LLAMA_PUBLIC_ENDPOINT
  model_id: meta-llama/Meta-Llama-3.1-8B-Instruct
system_prompt: You are an assistant for helping with math homework.
tools:
- component_type: ServerTool
  id: multiplication_tool
  name: multiplication_tool
  description: Tool that allows to compute multiplications
  metadata: {}
  inputs:
  - title: a
    type: integer
  - title: b
    type: integer
  outputs:
  - title: product
    type: integer
"""

multiplication_tool = ServerTool(
    name="multiplication_tool",
    description="Tool that allows to compute multiplications",
    parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
    output={"title": "product", "type": "integer"},
    func=lambda a, b: a * b,
)

tool_registry = {
    "multiplication_tool": multiplication_tool,
}

loader = AgentSpecLoader(tool_registry=tool_registry)
assistant = loader.load_yaml(AGENTSPEC_CONFIG)

if __name__ == "__main__":
    conversation = assistant.start_conversation()
    message_idx = 0
    while True:
        user_input = input("\nUSER >>> ")
        conversation.append_user_message(user_input)
        assistant.execute(conversation)
        messages = conversation.get_messages()
        for message in messages[message_idx + 1 :]:
            if message.message_type == MessageType.TOOL_REQUEST:
                print(f"\n{message.message_type.value} >>> {message.tool_requests}")
            else:
                print(f"\n{message.message_type.value} >>> {message.content}")
        message_idx = len(messages)
# .. end-full-code
