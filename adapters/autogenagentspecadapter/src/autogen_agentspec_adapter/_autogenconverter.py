# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.


import asyncio
import functools
import inspect
import typing
import warnings
from functools import partial
from textwrap import dedent
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast
from urllib.parse import urljoin

import httpx
from autogen_agentchat.agents import AssistantAgent as AutogenAssistantAgent
from autogen_agentspec_adapter._utils import render_template
from autogen_core.models import ChatCompletionClient as AutogenChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo
from autogen_core.tools import BaseTool
from autogen_core.tools import BaseTool as AutogenBaseTool
from autogen_core.tools import FunctionTool as AutogenFunctionTool
from autogen_ext.models.ollama import (
    OllamaChatCompletionClient as AutogenOllamaChatCompletionClient,
)
from autogen_ext.models.openai import (
    OpenAIChatCompletionClient as AutogenOpenAIChatCompletionClient,
)
from pydantic import BaseModel, Field, create_model

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.llms.vllmconfig import VllmConfig as AgentSpecVllmModel
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools.clienttool import ClientTool as AgentSpecClientTool
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool

from .functiontool import FunctionTool

_AutoGenTool = Union[AutogenFunctionTool, Callable[..., Any]]


def _create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    # Create a pydantic model whose attributes are the given properties
    fields: Dict[str, Any] = {}
    for property_ in properties:
        param_name = property_.title
        default = property_.default
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        fields[param_name] = (annotation, Field(default=default))
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


class AgentSpecToAutogenConverter:

    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, _AutoGenTool],
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
        tool_registry: Dict[str, _AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenChatCompletionClient:

        def _prepare_llm_args(
            agentspec_llm_: Union[AgentSpecVllmModel, AgentSpecOllamaModel],
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
            family = model_info.get("family", ModelFamily.UNKNOWN)
            structured_output = model_info.get("structured_output", True)
            return dict(
                model=agentspec_llm_.model_id,
                base_url=base_url,
                api_key="",
                model_info=ModelInfo(
                    vision=vision,
                    function_calling=function_calling,
                    json_output=json_output,
                    family=family,
                    structured_output=structured_output,
                ),
            )

        if isinstance(agentspec_llm, AgentSpecOpenAiConfig):
            return AutogenOpenAIChatCompletionClient(model=agentspec_llm.model_id)
        elif isinstance(agentspec_llm, AgentSpecVllmModel):
            return AutogenOpenAIChatCompletionClient(**_prepare_llm_args(agentspec_llm))
        elif isinstance(agentspec_llm, AgentSpecOllamaModel):
            return AutogenOllamaChatCompletionClient(**_prepare_llm_args(agentspec_llm))
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
        tool_registry: Dict[str, _AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenBaseTool[Any, Any]:
        if agentspec_tool.name in tool_registry:
            tool = tool_registry[agentspec_tool.name]
            if isinstance(tool, AutogenFunctionTool):
                return tool
            elif callable(tool):
                return AutogenFunctionTool(
                    name=agentspec_tool.name,
                    description=agentspec_tool.description or "",
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
        def _remote_tool(**kwargs: Any) -> Any:
            remote_tool_data = {k: render_template(v, kwargs) for k, v in remote_tool.data.items()}
            remote_tool_headers = {
                k: render_template(v, kwargs) for k, v in remote_tool.headers.items()
            }
            remote_tool_query_params = {
                k: render_template(v, kwargs) for k, v in remote_tool.query_params.items()
            }
            remote_tool_url = render_template(remote_tool.url, kwargs)
            response = httpx.request(
                method=remote_tool.http_method,
                url=remote_tool_url,
                params=remote_tool_query_params,
                data=remote_tool_data,
                headers=remote_tool_headers,
            )
            return response.json()

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
        tool_registry: Dict[str, _AutoGenTool],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> AutogenAssistantAgent:
        return AutogenAssistantAgent(
            # We interpret the name as the `name` of the agent in Autogen agent,
            # the system prompt as the `system_message`
            # This interpretation comes from the analysis of Autogen Agent definition examples
            name=agentspec_agent.name,
            system_message=agentspec_agent.system_prompt,
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
