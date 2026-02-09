# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, create_model

from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters.agent_framework._types import (
    AgentFrameworkComponent,
    AgentFrameworkMCPTool,
    AgentFrameworkTool,
    BaseChatClient,
    ChatAgent,
    FunctionTool,
    MCPStdioTool,
    MCPStreamableHTTPTool,
    OpenAIChatClient,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms.llmconfig import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.mcp.tools import MCPTool as AgentSpecMCPTool
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.tools import RemoteTool, ServerTool
from pyagentspec.tools import Tool as AgentSpecTool


def _create_pydantic_model_from_properties(
    model_name: str, properties: list[AgentSpecProperty]
) -> type[BaseModel]:
    # Create a pydantic model whose attributes are the given properties
    fields: dict[str, Any] = {}
    for property_ in properties:
        field_parameters: dict[str, Any] = {}
        param_name = property_.title
        if property_.default is not _agentspec_empty_default:
            field_parameters["default"] = property_.default
        if property_.description:
            field_parameters["description"] = property_.description
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        fields[param_name] = (annotation, Field(**field_parameters))
    return cast(type[BaseModel], create_model(model_name, **fields))


def _json_schema_type_to_python_annotation(json_schema: dict[str, Any]) -> str:
    if "anyOf" in json_schema:
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["anyOf"]
        )
        return f"Union[{','.join(possible_types)}]"
    json_schema_type = json_schema.get("type", "")
    if isinstance(json_schema_type, list):
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema_type
        )
        return f"Union[{','.join(possible_types)}]"

    if json_schema_type == "array":
        return f"List[{_json_schema_type_to_python_annotation(json_schema['items'])}]"
    mapping = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "boolean": "bool",
        "null": "None",
        "object": "Dict[str, Any]",
    }

    return mapping.get(json_schema_type, "Any")


class AgentSpecToAgentFrameworkConverter:
    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent] | None = None,
    ) -> AgentFrameworkComponent:
        """Convert the given PyAgentSpec component object into the corresponding Microsoft Agent Framework component"""
        if converted_components is None:
            converted_components = {}

        if agentspec_component.id in converted_components:
            return converted_components[agentspec_component.id]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        agent_framework_component: Any
        if isinstance(agentspec_component, AgentSpecAgent):
            agent_framework_component = self._agent_convert_to_agent_framework(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecLlmConfig):
            agent_framework_component = self._llm_convert_to_agent_framework(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecTool):
            agent_framework_component = self._tool_convert_to_agent_framework(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecComponent):
            raise NotImplementedError(
                f"The AgentSpec Component type '{agentspec_component.__class__.__name__}' is not yet supported "
                f"for conversion. Please contact the AgentSpec team."
            )
        else:
            raise TypeError(
                f"Expected object of type 'pyagentspec.component.Component',"
                f" but got {type(agentspec_component)} instead"
            )
        converted_components[agentspec_component.id] = agent_framework_component
        return converted_components[agentspec_component.id]

    def _tool_convert_to_agent_framework(
        self,
        tool: AgentSpecTool,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> AgentFrameworkTool:
        if isinstance(tool, ServerTool):
            return self._server_tool_convert_to_agent_framework(
                tool, tool_registry, converted_components
            )
        elif isinstance(tool, RemoteTool):
            return self._remote_tool_convert_to_agent_framework(
                tool, tool_registry, converted_components
            )
        elif isinstance(tool, AgentSpecMCPTool):
            return self._mcp_tool_convert_to_agent_framework(
                tool, tool_registry, converted_components
            )
        else:
            raise NotImplementedError(f"Tool of type {type(tool)} is not supported")

    def _mcp_tool_convert_to_agent_framework(
        self,
        mcp_tool: AgentSpecMCPTool,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> AgentFrameworkMCPTool:
        from pyagentspec.mcp.clienttransport import StdioTransport, StreamableHTTPTransport

        approval_mode = "always_require" if mcp_tool.requires_confirmation else None
        approval_mode = cast(Literal["always_require", "never_require"] | None, approval_mode)
        client_transport = mcp_tool.client_transport
        if isinstance(client_transport, StdioTransport):
            return MCPStdioTool(
                name=mcp_tool.name,
                description=mcp_tool.description,
                command=client_transport.command,
                args=client_transport.args,
                env=client_transport.env,
                approval_mode=approval_mode,
            )
        elif isinstance(client_transport, StreamableHTTPTransport):
            return MCPStreamableHTTPTool(
                name=mcp_tool.name,
                description=mcp_tool.description,
                url=client_transport.url,
                headers=client_transport.headers,
                approval_mode=approval_mode,
            )
        else:
            raise NotImplementedError(
                f"MCP Tool support for transport of type {type(client_transport)} is not supported yet"
            )

    def _remote_tool_convert_to_agent_framework(
        self,
        remote_tool: RemoteTool,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> AgentFrameworkTool:
        _remote_tool = _create_remote_tool_func(remote_tool)

        # Use a Pydantic model for args_schema
        args_model = _create_pydantic_model_from_properties(
            f"{remote_tool.name}Args",
            remote_tool.inputs or [],
        )

        aifunction = FunctionTool(
            name=remote_tool.name,
            description=remote_tool.description or "",
            input_model=args_model,
            func=_remote_tool,
            approval_mode=(
                "always_require" if remote_tool.requires_confirmation else "never_require"
            ),
        )
        return aifunction

    def _server_tool_convert_to_agent_framework(
        self,
        server_tool: ServerTool,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> AgentFrameworkTool:
        if server_tool.name not in tool_registry:
            raise ValueError(
                f"Tool `{server_tool.name}` was expected, but not found in tool registry"
            )
        function = tool_registry[server_tool.name]
        if callable(function):
            input_model = _create_pydantic_model_from_properties(
                f"{server_tool.name}Args",
                server_tool.inputs or [],
            )
            return FunctionTool(
                name=server_tool.name,
                func=function,
                description=server_tool.description or "",
                input_model=input_model,
                approval_mode=(
                    "always_require" if server_tool.requires_confirmation else "never_require"
                ),
            )
        return function

    def _llm_convert_to_agent_framework(
        self,
        llm_config: AgentSpecLlmConfig,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> BaseChatClient:
        if isinstance(llm_config, OpenAiCompatibleConfig):
            from urllib.parse import urljoin

            base_url = llm_config.url
            if not base_url.startswith("http://"):
                base_url = f"http://{base_url}"
            if "/v1" not in base_url:
                base_url = urljoin(base_url + "/", "v1")
            return OpenAIChatClient(
                api_key="openai",
                base_url=base_url,
                model_id=llm_config.model_id,
            )
        elif isinstance(llm_config, OllamaConfig):
            return OpenAIChatClient(
                api_key="ollama",
                base_url=llm_config.url,
                model_id=llm_config.model_id,
            )
        elif isinstance(llm_config, OpenAiConfig):
            return OpenAIChatClient(
                model_id=llm_config.model_id,
            )
        else:
            raise NotImplementedError(
                f"Llm model of type {llm_config.__class__.__name__} is not yet supported."
            )

    def _agent_convert_to_agent_framework(
        self,
        agent: AgentSpecAgent,
        tool_registry: dict[str, AgentFrameworkTool],
        converted_components: dict[str, AgentFrameworkComponent],
    ) -> AgentFrameworkComponent:
        generation_parameters = (
            agent.llm_config.default_generation_parameters or LlmGenerationConfig()
        )
        chat_client = self.convert(agent.llm_config, tool_registry, converted_components)
        tools = [self.convert(tool, tool_registry, converted_components) for tool in agent.tools]
        prompt = agent.system_prompt
        return ChatAgent(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            chat_client=cast(BaseChatClient, chat_client),
            tools=cast(AgentFrameworkTool, tools),
            instructions=prompt,
            temperature=generation_parameters.temperature,
            top_p=generation_parameters.top_p,
            max_tokens=generation_parameters.max_tokens,
        )
