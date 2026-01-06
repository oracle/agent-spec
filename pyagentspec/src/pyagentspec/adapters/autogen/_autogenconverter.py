# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import keyword
import re
from typing import Any, Dict, List, Optional, cast, get_args
from urllib.parse import urljoin

from pydantic import BaseModel, Field, create_model

from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters.autogen._functiontool import FunctionTool
from pyagentspec.adapters.autogen._types import (
    AutogenAssistantAgent,
    AutogenBaseTool,
    AutogenChatCompletionClient,
    AutogenFunctionTool,
    AutogenModelFamily,
    AutogenModelInfo,
    AutogenOllamaChatCompletionClient,
    AutogenOpenAIChatCompletionClient,
    AutoGenTool,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaicompatibleconfig import (
    OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleModel,
)
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools.clienttool import ClientTool as AgentSpecClientTool
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool


def literal_values(literal_type: Any) -> tuple[Any, ...]:
    return get_args(literal_type)


def fits_literal(value: Any, literal_type: Any) -> bool:
    return value in get_args(literal_type)


def _create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    # Create a pydantic model whose attributes are the given properties
    fields: Dict[str, Any] = {}
    for property_ in properties:
        field_parameters: Dict[str, Any] = {}
        param_name = property_.title
        if property_.default is not _agentspec_empty_default:
            field_parameters["default"] = property_.default
        if property_.description:
            field_parameters["description"] = property_.description
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        # Preserve description from spec so runtimes see the intended guidance
        fields[param_name] = (annotation, Field(**field_parameters))
    return cast(type[BaseModel], create_model(model_name, **fields))


def _json_schema_type_to_python_annotation(json_schema: Dict[str, Any]) -> str:
    if "anyOf" in json_schema:
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["anyOf"]
        )
        return f"Union[{','.join(possible_types)}]"
    if isinstance(json_schema["type"], list):
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["type"]
        )
        return f"Union[{','.join(possible_types)}]"

    if json_schema["type"] == "array":
        return f"List[{_json_schema_type_to_python_annotation(json_schema['items'])}]"
    mapping = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "boolean": "bool",
        "null": "None",
        "object": "Dict[str, Any]",
    }

    return mapping.get(json_schema["type"], "Any")


# Autogen requires that agent names be valid Python identifiers. Thus, we sanitize names to make sure they are valid.
def _sanitize_agent_name(name: str) -> str:
    # Replace non-identifier characters with underscores
    sanitized = re.sub(r"\W", "_", name or "")
    # Prefix underscore if it starts with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    # Ensure it's a valid identifier and not a Python keyword
    if not sanitized or not sanitized.isidentifier() or keyword.iskeyword(sanitized):
        sanitized = f"agent_{abs(hash(name)) % 10**8}"
    return sanitized


class AgentSpecToAutogenConverter:

    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Convert the given PyAgentSpec component object into the corresponding WayFlow component"""
        if converted_components is None:
            converted_components = {}

        if agentspec_component.id in converted_components:
            return converted_components[agentspec_component.id]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        autogen_component: Any
        if isinstance(agentspec_component, AgentSpecLlmConfig):
            autogen_component = self._llm_convert_to_autogen(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecAgent):
            autogen_component = self._agent_convert_to_autogen(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecTool):
            autogen_component = self._tool_convert_to_autogen(
                agentspec_component, tool_registry, converted_components
            )
        elif isinstance(agentspec_component, AgentSpecComponent):
            raise NotImplementedError(
                f"The Agent Spec Component type '{agentspec_component.__class__.__name__}' is not yet supported "
                f"for conversion. Please contact the AgentSpec team."
            )
        else:
            raise TypeError(
                f"Expected object of type 'pyagentspec.component.Component',"
                f" but got {type(agentspec_component)} instead"
            )
        converted_components[agentspec_component.id] = autogen_component
        return converted_components[agentspec_component.id]

    def _llm_convert_to_autogen(
        self,
        agentspec_llm: AgentSpecLlmConfig,
        tool_registry: Dict[str, AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenChatCompletionClient:

        def _prepare_llm_args(
            agentspec_llm_: AgentSpecOpenAiCompatibleModel,
        ) -> Dict[str, Any]:
            metadata = getattr(agentspec_llm_, "metadata", {}) or {}
            base_url = agentspec_llm_.url
            if not base_url.startswith("http://"):
                base_url = f"http://{base_url}"
            if "/v1" not in base_url:
                base_url = urljoin(base_url + "/", "v1")
            model_info = metadata.get("model_info") or {}
            vision = model_info.get("vision", True)
            function_calling = model_info.get("function_calling", True)
            json_output = model_info.get("json_output", True)
            family = model_info.get(
                "family",
                (
                    agentspec_llm_.model_id
                    if fits_literal(agentspec_llm_.model_id, AutogenModelFamily.ANY)
                    else AutogenModelFamily.UNKNOWN
                ),
            )
            structured_output = model_info.get("structured_output", True)
            return dict(
                model=agentspec_llm_.model_id,
                base_url=base_url,
                api_key="",
                model_info=AutogenModelInfo(
                    vision=vision,
                    function_calling=function_calling,
                    json_output=json_output,
                    family=family,
                    structured_output=structured_output,
                ),
            )

        if isinstance(agentspec_llm, AgentSpecOpenAiConfig):
            return AutogenOpenAIChatCompletionClient(model=agentspec_llm.model_id)
        elif isinstance(agentspec_llm, AgentSpecOllamaModel):
            return AutogenOllamaChatCompletionClient(**_prepare_llm_args(agentspec_llm))
        elif isinstance(agentspec_llm, AgentSpecOpenAiCompatibleModel):
            return AutogenOpenAIChatCompletionClient(**_prepare_llm_args(agentspec_llm))
        else:
            raise NotImplementedError(
                f"The provided LlmConfig type `{type(agentspec_llm)}` is not supported in autogen yet."
            )

    def _client_tool_convert_to_autogen(
        self, agentspec_client_tool: AgentSpecClientTool
    ) -> FunctionTool:
        def client_tool(**kwargs: Any) -> Any:
            tool_request = {
                "type": "client_tool_request",
                "name": agentspec_client_tool.name,
                "description": agentspec_client_tool.description,
                "inputs": kwargs,
            }
            response = input(f"{tool_request} -> ")
            return response

        client_tool.__name__ = agentspec_client_tool.name
        client_tool.__doc__ = agentspec_client_tool.description
        return FunctionTool(
            name=agentspec_client_tool.name,
            description=agentspec_client_tool.description or "",
            args_model=_create_pydantic_model_from_properties(
                agentspec_client_tool.name.title() + "InputSchema",
                agentspec_client_tool.inputs or [],
            ),
            func=client_tool,
        )

    def _tool_convert_to_autogen(
        self,
        agentspec_tool: AgentSpecTool,
        tool_registry: Dict[str, AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenBaseTool[Any, Any]:
        if agentspec_tool.name in tool_registry:
            tool = tool_registry[agentspec_tool.name]
            if isinstance(tool, AutogenFunctionTool):
                # If the registry already supplies an Autogen tool, use it as-is.
                # Note: this will keep the tool's own description/schema.
                return tool
            elif callable(tool):
                # Build a FunctionTool that enforces the spec's description and input schema
                return FunctionTool(
                    name=agentspec_tool.name,
                    description=agentspec_tool.description or "",
                    args_model=_create_pydantic_model_from_properties(
                        agentspec_tool.name.title() + "InputSchema",
                        agentspec_tool.inputs or [],
                    ),
                    func=tool,
                )
            else:
                raise ValueError(
                    f"Unsupported type of ServerTool `{agentspec_tool.name}`: {type(tool)}"
                )
        if isinstance(agentspec_tool, AgentSpecServerTool):
            raise ValueError(
                f"The implementation of the ServerTool `{agentspec_tool.name}` "
                f"must be provided in the tool registry"
            )
        elif isinstance(agentspec_tool, AgentSpecClientTool):
            return self._client_tool_convert_to_autogen(agentspec_tool)
        elif isinstance(agentspec_tool, AgentSpecRemoteTool):
            return self._remote_tool_convert_to_autogen(agentspec_tool)
        else:
            raise TypeError(f"AgentSpec Tool of type {type(agentspec_tool)} is not supported")

    def _remote_tool_convert_to_autogen(self, remote_tool: AgentSpecRemoteTool) -> FunctionTool:
        _remote_tool = _create_remote_tool_func(remote_tool)
        _remote_tool.__name__ = remote_tool.name
        _remote_tool.__doc__ = remote_tool.description
        return FunctionTool(
            name=remote_tool.name,
            description=remote_tool.description or "",
            args_model=_create_pydantic_model_from_properties(
                remote_tool.name.title() + "InputSchema", remote_tool.inputs or []
            ),
            func=_remote_tool,
        )

    def _agent_convert_to_autogen(
        self,
        agentspec_agent: AgentSpecAgent,
        tool_registry: Dict[str, AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenAssistantAgent:
        return AutogenAssistantAgent(
            # We interpret the name as the `name` of the agent in Autogen agent,
            # the system prompt as the `system_message`
            # This interpretation comes from the analysis of Autogen Agent definition examples
            name=_sanitize_agent_name(agentspec_agent.name),
            system_message=agentspec_agent.system_prompt,
            reflect_on_tool_use=len(agentspec_agent.tools) > 0,
            model_client=(
                self.convert(
                    agentspec_agent.llm_config,
                    tool_registry=tool_registry,
                    converted_components=converted_components,
                )
                if agentspec_agent.llm_config is not None
                else (_ for _ in ()).throw(ValueError("agentspec_agent.llm_config cannot be None"))
            ),
            tools=[
                self.convert(
                    tool, tool_registry=tool_registry, converted_components=converted_components
                )
                for tool in agentspec_agent.tools
            ],
        )
