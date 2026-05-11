# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyagentspec[langgraph]==26.1.0",
#   "wayflowcore==26.1.0",
# ]
# ///

import os
from pathlib import Path
from typing import cast

from pyagentspec.flows.flowbuilder import FlowBuilder
from pyagentspec.flows.nodes import LlmNode, MapNode, ToolNode
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.property import ListProperty, Property, StringProperty, UnionProperty
from pyagentspec.tools import ServerTool

MAX_FILES: int | None = None


def get_path_of_public_apis(source_path: str) -> list[str]:
    paths: list[str] = []
    for root, _, files in os.walk(source_path):
        root_path = Path(root)
        if root_path.name.startswith("_"):
            continue
        for file in files:
            if file.startswith("_") or not file.endswith(".py"):
                continue
            paths.append(f"{root}/{file}")
    # Limit number of files for testing purposes
    if MAX_FILES and MAX_FILES > 0:
        paths = paths[:MAX_FILES]
    return paths


source_path_prop = StringProperty(title="source_path")
public_api_paths_prop = ListProperty(title="public_api_paths", item_type=StringProperty())
file_path_prop = StringProperty(title="file_path")
file_paths_prop = ListProperty(title="file_paths", item_type=file_path_prop)
file_content_prop = StringProperty(title="file_content")
generated_text_prop = StringProperty(title="generated_text")
collected_file_path_prop = ListProperty(title="collected_file_path", item_type=file_path_prop)
llms_txt_prop = StringProperty(title="llms_txt")
collected_generated_text_prop = ListProperty(
    title="collected_generated_text",
    item_type=generated_text_prop,
    default=[],
)
iterated_file_path_prop = UnionProperty(
    title="iterated_file_path",
    any_of=[
        file_path_prop,
        file_paths_prop,
    ],
)


# ToolNode to list all the public apis in the codebase
list_public_apis_tool = ServerTool(
    name="get_path_of_public_apis",
    inputs=[source_path_prop],
    outputs=[public_api_paths_prop],
)

list_public_apis_node = ToolNode(
    name="get_public_apis_node",
    tool=list_public_apis_tool,
)

# ToolNode to read a file's contents
read_file_tool = ServerTool(
    name="read_file",
    inputs=[file_path_prop],
    outputs=[file_content_prop],
)
read_file_node = ToolNode(name="read_file_node", tool=read_file_tool)

LLM_TXT_GENERATION_PROMPT = '''
Given a file from a codebase, write a compact summary of the public APIs, following the requested format.

Instructions:
- Remove imports
- Remove private classes and functions (private = leading with an underscore `_`)
- Remove private methods, classvars and attributes of classes
- Keep the examples but remove the rest of the docstrings
- Simplify classvar docstring when non-informative
- Keep only one example from the docstring preferably, the one that would be most general and useful for the LLM

If there are multiple classes/functions in a given file, include them all (as long as they are public).
If you find an attribute that is not meant to be known or used publicly (such as the min version attribute in Component) you can also discard it in your output.


Example:
<example>
<input_file>
"""This module defines several Agent Spec components."""

from typing import List

from pydantic import Field, SerializeAsAny

from pyagentspec.agenticcomponent import AgenticComponent
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.property import Property
from pyagentspec.templating import get_placeholder_properties_from_json_object
from pyagentspec.tools.tool import Tool
from pyagentspec.tools.toolbox import ToolBox
from pyagentspec.versioning import AgentSpecVersionEnum


class Agent(AgenticComponent):
    """
    An agent is a component that can do several rounds of conversation to solve a task.

    It can be executed by itself, or be executed in a flow using an AgentNode.


    Examples
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.property import Property
    >>> expertise_property=Property(
    ...     json_schema={"title": "domain_of_expertise", "type": "string"}
    ... )
    >>> system_prompt = """You are an expert in {domain_of_expertise}.
    ... Please help the users with their requests."""
    >>> agent = Agent(
    ...     name="Adaptive expert agent",
    ...     system_prompt=system_prompt,
    ...     llm_config=llm_config,
    ...     inputs=[expertise_property],
    ... )

    """

    llm_config: SerializeAsAny[LlmConfig]
    """Configuration of the LLM to use for this Agent"""
    system_prompt: str
    """Initial system prompt used for the initialization of the agent's context"""
    tools: List[SerializeAsAny[Tool]] = Field(default_factory=list)
    """List of tools that the agent can use to fulfil user requests"""
    toolboxes: List[SerializeAsAny[ToolBox]] = Field(default_factory=list)
    """List of toolboxes that are passed to the agent."""
    human_in_the_loop: bool = True
    """Flag that determines if the Agent can request input from the user."""

    def _get_inferred_inputs(self) -> List[Property]:
        # Extract all the placeholders in the prompt and make them string inputs by default
        return get_placeholder_properties_from_json_object(getattr(self, "system_prompt", ""))

    def _get_inferred_outputs(self) -> List[Property]:
        return self.outputs or []

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("toolboxes")
            fields_to_exclude.add("human_in_the_loop")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.toolboxes or not self.human_in_the_loop:
            # We first check if the component requires toolboxes)
            # If that's the case, we set the min version to 25.4.2, when toolboxes were introduced
            # Similarly, human_in_the_loop was only added in 25.4.2 (human_in_the_loop=True was
            # the de-facto default before)
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(parent_min_version, current_object_min_version)

</input_file>

The following would be accepted:
<answer>
# pyagentspec.agent.Agent
class Agent(AgenticComponent):
    # can do several rounds of conversations to solve a task
    # can be used in Flow with AgentNode
    """
    Example
    --------
    >>> from pyagentspec.agent import Agent
    >>> from pyagentspec.property import Property
    >>> expertise_property=Property(
    ...     json_schema={"title": "domain_of_expertise", "type": "string"}
    ... )
    >>> system_prompt = """You are an expert in {domain_of_expertise}.
    ... Please help the users with their requests."""
    >>> agent = Agent(
    ...     name="Adaptive expert agent",
    ...     system_prompt=system_prompt,
    ...     llm_config=llm_config,
    ...     inputs=[expertise_property],
    ... )
    """

    llm_config: LlmConfig
    system_prompt: str # prompt used for the initialization of the agent's context
    tools: List[Tool] = Field(default_factory=list)
    toolboxes: List[ToolBox] = Field(default_factory=list)
    human_in_the_loop: bool = True # whether the Agent can request input from the user

</answer>
</example>

---

Here is the file:
<file_path>
{{file_path}}
</file_path>
<input_file>
{{file_content}}
</input_file>
'''

# LLM node to generate compact documentation for one file
generate_node = LlmNode(
    name="llms_txt_generator",
    llm_config=OpenAiCompatibleConfig(
        name="gpt-oss-120b",
        url=os.environ["OSS_API_URL"],
        model_id="openai/gpt-oss-120b",
    ),
    prompt_template=LLM_TXT_GENERATION_PROMPT,
    inputs=[
        file_content_prop,
        file_path_prop,
    ],
    outputs=[generated_text_prop],
)

concat_docs_tool = ServerTool(
    name="concat_compact_docs",
    inputs=[collected_file_path_prop, collected_generated_text_prop],
    outputs=[llms_txt_prop],
)
concat_docs_node = ToolNode(
    name="concat_docs_node",
    tool=concat_docs_tool,
)

# Map subflow, to generate a compact documentation using an llm, given a file path
builder = FlowBuilder()
## Nodes
builder.add_node(read_file_node).add_node(generate_node)
builder.set_entry_point(read_file_node, [file_path_prop])
builder.set_finish_points(generate_node, cast(list[Property], [generated_text_prop]))

## Control Flow Edges
builder.add_edge(read_file_node, generate_node)

## Data Flow Edges
builder.add_data_edge("StartNode", read_file_node, file_path_prop.title)
builder.add_data_edge("StartNode", generate_node, file_path_prop.title)
builder.add_data_edge(read_file_node, generate_node, file_content_prop.title)
builder.add_data_edge(generate_node, "EndNode_1", generated_text_prop.title)
map_subflow = builder.build("GenerateCompactDocSubflow")

# Map over all public API paths and collect results
map_node = MapNode(
    name="map_public_apis",
    subflow=map_subflow,
    inputs=[iterated_file_path_prop],
    outputs=[collected_generated_text_prop],
)

# Top-level flow: list -> map -> concat
builder = FlowBuilder()
builder.add_sequence(
    [
        list_public_apis_node,
        map_node,
        concat_docs_node,
    ]
)
builder.set_entry_point(list_public_apis_node, [source_path_prop])
builder.set_finish_points(concat_docs_node, cast(list[Property], [llms_txt_prop]))
builder.add_data_edge(
    "StartNode",
    list_public_apis_node,
    source_path_prop.title,
)
builder.add_data_edge(
    list_public_apis_node, map_node, (public_api_paths_prop.title, iterated_file_path_prop.title)
)
builder.add_data_edge(
    map_node,
    concat_docs_node,
    collected_generated_text_prop.title,
)
builder.add_data_edge(
    list_public_apis_node,
    concat_docs_node,
    (public_api_paths_prop.title, collected_file_path_prop.title),
)
builder.add_data_edge(concat_docs_node, "EndNode_1", llms_txt_prop.title)
flow = builder.build("GenerateLLMsTxtFlow")


# Load into WayFlow
def read_file(file_path: str) -> str:
    return Path(file_path).read_text()


def concat_compact_docs(
    collected_file_path: list[str],
    collected_generated_text: list[str],
) -> str:
    from textwrap import dedent

    result = ""
    for path, content in zip(collected_file_path, collected_generated_text):
        line = path
        result += dedent(f"""
{"-" * len(line)}
{line}
{"-" * len(line)}

{content}
            """)
    return result


def _resolve_default_src_path() -> str:
    return str((Path(__file__).parent.parent.parent.parent.parent / "pyagentspec/src/").resolve())


def run_and_write_with_wayflow() -> Path:
    from wayflowcore.agentspec import AgentSpecLoader
    from wayflowcore.executors.executionstatus import FinishedStatus
    from wayflowcore.flow import Flow as WayFlowFlow

    wayflow_loader = AgentSpecLoader(
        tool_registry={
            "get_path_of_public_apis": get_path_of_public_apis,
            "read_file": read_file,
            "concat_compact_docs": concat_compact_docs,
        }
    )

    wayflow_flow = wayflow_loader.load_component(flow)
    if not isinstance(wayflow_flow, WayFlowFlow):
        raise RuntimeError("Failed to load WayFlow flow from Agent Spec configuration")

    src = _resolve_default_src_path()
    conversation = wayflow_flow.start_conversation({"source_path": src})
    status = wayflow_flow.execute(conversation)
    if not isinstance(status, FinishedStatus):
        raise RuntimeError("Flow didn't finish execution as expected")
    llms_txt = status.output_values["llms_txt"]

    out_file = Path("generated-llms.txt")
    out_file.write_text(llms_txt)

    return out_file


def run_and_write_with_langgraph() -> Path:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    langgraph_loader = AgentSpecLoader(
        tool_registry={
            "get_path_of_public_apis": get_path_of_public_apis,
            "read_file": read_file,
            "concat_compact_docs": concat_compact_docs,
        }
    )
    langgraph_flow = langgraph_loader.load_component(flow)

    src = _resolve_default_src_path()
    result = langgraph_flow.invoke({"inputs": {"source_path": src}})
    llms_txt: str = result["outputs"]["llms_txt"]

    out_file = Path("generated-llms.txt")
    out_file.write_text(llms_txt.strip())

    return out_file


if __name__ == "__main__":
    ##  Run with WayFlow
    # out_path = run_and_write_with_wayflow()

    # Run with LangGraph
    out_path = run_and_write_with_langgraph()

    print(f"Wrote to file: {out_path}")
