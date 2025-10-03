# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

# .. start-llm
from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)
# .. end-llm

# .. start-agent
from pyagentspec.agent import Agent

agent = Agent(
    name="Helpful agent",
    llm_config=llm_config,
    system_prompt="""Your a helpful writing assistant. Answer the user's questions about article writing.
Make sure to welcome the user first, but keep it short""",
)
# .. end-agent

# .. start-custom-prompt-agent
from pyagentspec.agent import Agent
from pyagentspec.property import StringProperty

agent = Agent(
    name="Helpful agent with username",
    llm_config=llm_config,
    system_prompt="""Your a helpful writing assistant. Answer the user's questions about article writing.
Make sure to welcome the user first, their name is {{user_name}}, but keep it short""",
    inputs=[StringProperty(title="user_name")]
)
# .. end-custom-prompt-agent

# .. start-tools
from pyagentspec.property import ListProperty
from pyagentspec.tools import ServerTool

tools = [
    ServerTool(
        name="get_synonyms",
        description="Given a word, return the list of synonyms according to the vocabulary",
        inputs=[StringProperty(title="word")],
        outputs=[ListProperty(title="synonyms", item_type=StringProperty(title="word"))]
    ),
    ServerTool(
        name="pretty_formatting",
        description="Given a paragraph, format the paragraph to fix spaces, newlines, indentation, etc.",
        inputs=[StringProperty(title="paragraph")],
        outputs=[StringProperty(title="formatted_paragraph")]
    ),
]

agent = Agent(
    name="Helpful agent with username and tools",
    llm_config=llm_config,
    system_prompt="""Your a helpful writing assistant. Answer the user's questions about article writing.
Make sure to welcome the user first, their name is {{user_name}}, but keep it short""",
    tools=tools,
    inputs=[StringProperty(title="user_name")]
)
# .. end-tools

# .. start-export-config-to-agentspec
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(agent)
# .. end-export-config-to-agentspec

# .. start-full-code
from pyagentspec.agent import Agent
from pyagentspec.llms import VllmConfig
from pyagentspec.property import ListProperty, StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ServerTool

llm_config = VllmConfig(
    name="vllm-llama-4-maverick",
    model_id="llama-4-maverick",
    url="http://url.to.my.vllm.server/llama4mav",
)

tools = [
    ServerTool(
        name="get_synonyms",
        description="Given a word, return the list of synonyms according to the vocabulary",
        inputs=[StringProperty(title="word")],
        outputs=[ListProperty(title="synonyms", item_type=StringProperty(title="word"))]
    ),
    ServerTool(
        name="pretty_formatting",
        description="Given a paragraph, format the paragraph to fix spaces, newlines, indentation, etc.",
        inputs=[StringProperty(title="paragraph")],
        outputs=[StringProperty(title="formatted_paragraph")]
    ),
]

agent = Agent(
    name="Helpful agent with username and tools",
    llm_config=llm_config,
    system_prompt="""Your a helpful writing assistant. Answer the user's questions about article writing.
Make sure to welcome the user first, their name is {{user_name}}, but keep it short""",
    tools=tools,
    inputs=[StringProperty(title="user_name")]
)

serialized_assistant = AgentSpecSerializer().to_json(agent)
# .. end-full-code
