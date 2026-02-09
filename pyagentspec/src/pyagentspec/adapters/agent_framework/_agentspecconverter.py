# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import typing
from typing import Any, Union, cast, get_args, get_origin, get_type_hints

from pyagentspec.adapters.agent_framework._types import (
    AgentFrameworkLlmConfig,
    AgentFrameworkMCPTool,
    AgentFrameworkTool,
    ChatAgent,
    FunctionTool,
    MCPStdioTool,
    MCPStreamableHTTPTool,
    OpenAIChatClient,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.mcp.clienttransport import StdioTransport, StreamableHTTPTransport
from pyagentspec.mcp.tools import MCPTool
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import ServerTool
from pyagentspec.tools import Tool as AgentSpecTool


def _get_obj_reference(obj: Any) -> str:
    return f"{obj.__class__.__name__.lower()}/{id(obj)}"


def _python_type_to_jsonschema(py_type: Any) -> dict[str, Any]:
    origin = get_origin(py_type)
    args = get_args(py_type)
    if py_type is int:
        return {"type": "integer"}
    elif py_type is float:
        return {"type": "number"}
    elif py_type is str:
        return {"type": "string"}
    elif py_type is bool:
        return {"type": "boolean"}
    elif py_type is None:
        return {"type": "null"}
    elif origin is list:
        return {"type": "array", "items": _python_type_to_jsonschema(args[0])}
    elif origin is dict:
        return {"type": "object"}
    elif origin is Union:
        return {"anyOf": [_python_type_to_jsonschema(a) for a in args if a is not type(None)]}
    else:
        return {}


def _input_hints_to_json_schema(hints: dict[str, Any]) -> dict[str, Any]:
    hints = hints.copy()
    if "return" in hints:
        hints.pop("return")
    inputs = {}
    for title, type in hints.items():
        inputs[title] = _python_type_to_jsonschema(type)
    return inputs


def _return_type_hints_to_json_schema(hints: dict[str, Any]) -> dict[str, Any]:
    return_type_hint = hints.get("return", str)
    return _python_type_to_jsonschema(return_type_hint)


def _json_schema_to_property(title: str, json_schema: dict[str, Any]) -> AgentSpecProperty:
    return AgentSpecProperty(title=title, json_schema=json_schema)


class AgentFrameworkToAgentSpecConverter:

    def convert(
        self,
        agent_framework_component: Any,
        referenced_objects: dict[str, AgentSpecComponent] | None = None,
    ) -> AgentSpecComponent:
        """Convert the given Microsoft Agent Framework component object into the corresponding PyAgentSpec component"""

        if referenced_objects is None:
            referenced_objects = dict()

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = _get_obj_reference(agent_framework_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        agentspec_component: AgentSpecComponent
        if isinstance(agent_framework_component, ChatAgent):
            agentspec_component = self._agent_convert_to_agentspec(
                agent_framework_component,
                referenced_objects,
            )
        elif isinstance(agent_framework_component, AgentFrameworkLlmConfig):
            agentspec_component = self._llm_convert_to_agentspec(
                agent_framework_component,
                referenced_objects,
            )
        elif isinstance(agent_framework_component, AgentFrameworkMCPTool):
            agentspec_component = self._mcp_tool_convert_to_agentspec(
                agent_framework_component,
                referenced_objects,
            )
        elif isinstance(agent_framework_component, typing.get_args(AgentFrameworkTool)):
            agentspec_component = self._tool_convert_to_agentspec(
                agent_framework_component,
                referenced_objects,
            )
        else:
            raise NotImplementedError(
                f"The AgentFramework type '{agent_framework_component.__class__.__name__}' is not yet supported "
                f"for conversion. Please contact the AgentSpec team."
            )
        referenced_objects[object_reference] = agentspec_component
        return referenced_objects[object_reference]

    def _mcp_tool_convert_to_agentspec(
        self,
        mcp_tool: AgentFrameworkMCPTool,
        referenced_objects: dict[str, AgentSpecComponent],
    ) -> MCPTool:
        if isinstance(mcp_tool, MCPStdioTool):
            return MCPTool(
                name=mcp_tool.name,
                description=mcp_tool.description,
                client_transport=StdioTransport(
                    name=f"{mcp_tool.name}_transport",
                    command=mcp_tool.command,
                ),
                requires_confirmation=mcp_tool.approval_mode == "always_require",
            )
        elif isinstance(mcp_tool, MCPStreamableHTTPTool):
            return MCPTool(
                name=mcp_tool.name,
                description=mcp_tool.description,
                client_transport=StreamableHTTPTransport(
                    name=f"{mcp_tool.name}_transport",
                    url=mcp_tool.url,
                ),
                requires_confirmation=mcp_tool.approval_mode == "always_require",
            )
        else:
            raise NotImplementedError(
                f"mcp tool conversion to agentspec for type {type(mcp_tool)} not supported yet"
            )

    def _tool_convert_to_agentspec(
        self,
        tool: AgentFrameworkTool,
        referenced_objects: dict[str, AgentSpecComponent],
    ) -> AgentSpecTool:
        requires_confirmation = False
        callable_tool: Any = tool
        tool_description: str | None = None
        if isinstance(tool, FunctionTool):
            requires_confirmation = tool.approval_mode == "always_require"
            tool_description = tool.description
            callable_tool = tool.func

        if not callable(callable_tool):
            raise NotImplementedError("Other tool types not supported yet")

        hints = get_type_hints(callable_tool)
        input_properties = [
            _json_schema_to_property(title, json_schema)
            for title, json_schema in _input_hints_to_json_schema(hints).items()
        ]
        output_schema = _return_type_hints_to_json_schema(hints)
        output_property = _json_schema_to_property(title="result", json_schema=output_schema)

        return ServerTool(
            name=callable_tool.__name__,
            inputs=input_properties,
            outputs=[output_property],
            description=tool_description or callable_tool.__doc__,
            requires_confirmation=requires_confirmation,
        )

    def _llm_convert_to_agentspec(
        self,
        chat_client: AgentFrameworkLlmConfig,
        referenced_objects: dict[str, AgentSpecComponent],
    ) -> OpenAiCompatibleConfig:
        if isinstance(chat_client, OpenAIChatClient):
            if chat_client.model_id is None:
                # Defensive check for None in some versions due to fast iteration
                # Once the framework stabilizes and the type is set in stone this check can be removed
                raise ValueError(f"model_id for {type(chat_client)} is not set.")
            return OpenAiCompatibleConfig(
                name=chat_client.model_id,
                model_id=chat_client.model_id,
                url=chat_client.service_url(),
            )
        else:
            raise NotImplementedError(f"Chat client {type(chat_client)} not supported")

    def _agent_convert_to_agentspec(
        self,
        chat_agent: ChatAgent,
        referenced_objects: dict[str, AgentSpecComponent],
    ) -> AgentSpecComponent:
        generation_config = LlmGenerationConfig(
            temperature=chat_agent.additional_properties.get("temperature", None),
            top_p=chat_agent.additional_properties.get("top_p", None),
            max_tokens=chat_agent.additional_properties.get("max_tokens", None),
        )
        llm_config = cast(
            LlmConfig,
            self.convert(
                chat_agent.chat_client,
                referenced_objects,
            ),
        )
        llm_config.default_generation_parameters = generation_config
        system_prompt = chat_agent.default_options.get("instructions", "")
        tools = [
            cast(AgentSpecTool, self.convert(tool))
            for tool in chat_agent.default_options.get("tools", [])
        ]
        return AgentSpecAgent(
            id=chat_agent.id,
            name=chat_agent.name or "AgentFramework Agent",
            description=chat_agent.description,
            llm_config=llm_config,
            system_prompt=system_prompt,
            tools=tools,
        )
