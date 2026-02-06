# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors


import random
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from pyagentspec.adapters.langgraph import AgentSpecLoader

""" Example program output:
User> What is the weather like in Agadir?
Agent: The weather in Agadir is sunny.
User> What about Rabat?
Agent: The weather in Rabat is cloudy.
"""

agent_yaml = """
component_type: Agent
description: ''
id: 42e2724d-ef9c-4c63-b5fd-07aa59697d95
inputs: []
llm_config:
  component_type: VllmConfig
  default_generation_parameters: null
  description: null
  id: 01932e0d-5115-4848-a529-f1f1f7a5e866
  metadata:
    __metadata_info__: {}
  model_id: /storage/models/Llama-3.3-70B-Instruct
  name: Llama-3.3-70B-Instruct
  url: url.to.your.llm
metadata:
  __metadata_info__: {}
name: agent_75dd14fc
outputs: []
system_prompt: You are a weather agent. Use tools to answer user questions.
tools:
- component_type: ClientTool
  description: Returns the weather in a certain city
  id: 19d2e6d9-cddb-4d96-a536-1c6dd007d4e0
  inputs:
  - title: city
    type: string
  metadata:
    __metadata_info__: {}
  name: get_weather
  outputs:
  - title: tool_output
    type: string
agentspec_version: 25.4.1
"""

agent = AgentSpecLoader(checkpointer=MemorySaver()).load_yaml(agent_yaml)
config = RunnableConfig({"configurable": {"thread_id": "1"}})
result: Optional[Any] = None
try:
    while True:
        if result is not None and "__interrupt__" in result:
            weather = random.choice(  # nosec: Not used for cryptography
                ["sunny", "cloudy", "windy"]
            )
            result = agent.invoke(
                input=Command(resume={"weather": weather}),
            )
        else:
            if result is not None:
                print(f"Agent: {result['messages'][-1].content}")
            user_input = input("User> ")
            messages = {"messages": [{"role": "user", "content": user_input}]}
            result = agent.invoke(messages, config)
except (EOFError, KeyboardInterrupt):
    pass
