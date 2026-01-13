# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, create_model

from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters.crewai._types import (
    CrewAIAgent,
    CrewAIBaseTool,
    CrewAILlm,
    CrewAIServerToolType,
    CrewAITool,
)
from pyagentspec.adapters.crewai.tracing import CrewAIAgentWithTracing
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaicompatibleconfig import (
    OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig,
)
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.llms.vllmconfig import VllmConfig as AgentSpecVllmModel
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.tools import Tool as AgentSpecTool
from pyagentspec.tools.clienttool import ClientTool as AgentSpecClientTool
from pyagentspec.tools.remotetool import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools.servertool import ServerTool as AgentSpecServerTool


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
    mapping = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "boolean": "bool",
        "null": "None",
    }
    if json_schema["type"] == "object":
        # We could do better in inferring the type of values, for now we just use Any
        return "Dict[str, Any]"
    if json_schema["type"] == "array":
        return f"List[{_json_schema_type_to_python_annotation(json_schema['items'])}]"
    return mapping.get(json_schema["type"], "Any")


def _create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    """Create a Pydantic model CLASS whose attributes are the given properties."""
    fields: Dict[str, Any] = {}
    for property_ in properties:
        field_parameters: Dict[str, Any] = {}
        param_name = property_.title
        if property_.default is not _agentspec_empty_default:
            field_parameters["default"] = property_.default
        if property_.description:
            field_parameters["description"] = property_.description
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        fields[param_name] = (annotation, Field(**field_parameters))
    return create_model(model_name, **fields)


class AgentSpecToCrewAIConverter:

    def __init__(self, enable_agentspec_tracing: bool = True) -> None:
        self.enable_agentspec_tracing = enable_agentspec_tracing
        self._is_root_call: bool = True
        self._obj_id_to_agentspec_component: Dict[int, AgentSpecComponent] = {}

    def convert(
        self,
        agentspec_component: AgentSpecComponent,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Convert the given PyAgentSpec component object into the corresponding CrewAI component"""
        if converted_components is None:
            converted_components = {}

        if self._is_root_call:
            # Reset the obj id -> agentspec component mapping
            self._obj_id_to_agentspec_component = {}

        is_root_call = self._is_root_call
        self._is_root_call = False

        if agentspec_component.id not in converted_components:
            # If we did not find the object, we create it, and we record it in the referenced_objects registry
            crewai_component: Any
            if isinstance(agentspec_component, AgentSpecLlmConfig):
                crewai_component = self._llm_convert_to_crewai(
                    agentspec_component, tool_registry, converted_components
                )
            elif isinstance(agentspec_component, AgentSpecAgent):
                crewai_component = self._agent_convert_to_crewai(
                    agentspec_component, tool_registry, converted_components
                )
            elif isinstance(agentspec_component, AgentSpecTool):
                crewai_component = self._tool_convert_to_crewai(
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
            converted_components[agentspec_component.id] = crewai_component

        converted_crewai_component = converted_components[agentspec_component.id]
        self._obj_id_to_agentspec_component[id(converted_crewai_component)] = agentspec_component

        if (
            is_root_call
            and self.enable_agentspec_tracing
            and isinstance(converted_crewai_component, CrewAIAgentWithTracing)
        ):
            # If the root component is an agent to which we can attach an agent spec listener,
            # we monkey patch the root CrewAI component to attach the event listener for Agent Spec
            from pyagentspec.adapters.crewai.tracing import AgentSpecEventListener

            converted_crewai_component._agentspec_event_listener = AgentSpecEventListener(
                agentspec_components=self._obj_id_to_agentspec_component
            )

        self._is_root_call = is_root_call
        return converted_crewai_component

    def _llm_convert_to_crewai(
        self,
        agentspec_llm: AgentSpecLlmConfig,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> CrewAILlm:

        def parse_url(url: str) -> str:
            url = url.strip()
            if url.endswith("/completions"):
                return url
            if not url.endswith("/v1") and not url.endswith("/litellm"):
                url += "/v1"
            if not url.startswith("http"):
                url = "http://" + url
            return url

        llm_parameters: Dict[str, Any] = {}
        if isinstance(agentspec_llm, AgentSpecOpenAiConfig):
            llm_parameters["model"] = "openai/" + agentspec_llm.model_id
        elif isinstance(agentspec_llm, AgentSpecVllmModel):
            # CrewAI uses lite llm underneath:
            # https://community.crewai.com/t/help-how-to-use-a-custom-local-llm-with-vllm/5746
            llm_parameters["model"] = "hosted_vllm/" + agentspec_llm.model_id
            llm_parameters["api_base"] = parse_url(agentspec_llm.url)
        elif isinstance(agentspec_llm, AgentSpecOpenAiCompatibleConfig):
            llm_parameters["model"] = "openai/" + agentspec_llm.model_id
            llm_parameters["api_base"] = parse_url(agentspec_llm.url)
        elif isinstance(agentspec_llm, AgentSpecOllamaModel):
            llm_parameters["model"] = "ollama/" + agentspec_llm.model_id
            llm_parameters["base_url"] = parse_url(agentspec_llm.url)
        else:
            raise NotImplementedError()

        if agentspec_llm.default_generation_parameters is not None:
            llm_parameters["top_p"] = agentspec_llm.default_generation_parameters.top_p
            llm_parameters["temperature"] = agentspec_llm.default_generation_parameters.temperature
            llm_parameters["max_tokens"] = agentspec_llm.default_generation_parameters.max_tokens

        return CrewAILlm(**llm_parameters)

    def _tool_convert_to_crewai(
        self,
        agentspec_tool: AgentSpecTool,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> CrewAIBaseTool:
        if agentspec_tool.name in tool_registry:
            tool = tool_registry[agentspec_tool.name]
            if isinstance(tool, CrewAITool):
                return tool
            elif callable(tool):
                return CrewAITool(
                    name=agentspec_tool.name,
                    description=agentspec_tool.description or "",
                    args_schema=_create_pydantic_model_from_properties(
                        agentspec_tool.name.title() + "InputSchema", agentspec_tool.inputs or []
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

            def client_tool(**kwargs: Any) -> Any:
                tool_request = {
                    "type": "client_tool_request",
                    "name": agentspec_tool.name,
                    "description": agentspec_tool.description,
                    "inputs": kwargs,
                }
                response = input(f"{tool_request} -> ")
                return response

            client_tool.__name__ = agentspec_tool.name
            client_tool.__doc__ = agentspec_tool.description
            return CrewAITool(
                name=agentspec_tool.name,
                description=agentspec_tool.description or "",
                args_schema=_create_pydantic_model_from_properties(
                    agentspec_tool.name.title() + "InputSchema", agentspec_tool.inputs or []
                ),
                func=client_tool,
            )
        elif isinstance(agentspec_tool, AgentSpecRemoteTool):
            return self._remote_tool_convert_to_crewai(agentspec_tool)
        raise ValueError(
            f"Tools of type {type(agentspec_tool)} are not yet supported for translation to CrewAI"
        )

    def _remote_tool_convert_to_crewai(self, remote_tool: AgentSpecRemoteTool) -> CrewAIBaseTool:
        _remote_tool = _create_remote_tool_func(remote_tool)
        _remote_tool.__name__ = remote_tool.name
        _remote_tool.__doc__ = remote_tool.description
        return CrewAITool(
            name=remote_tool.name,
            description=remote_tool.description or "",
            args_schema=_create_pydantic_model_from_properties(
                remote_tool.name.title() + "InputSchema", remote_tool.inputs or []
            ),
            func=_remote_tool,
        )

    def _agent_convert_to_crewai(
        self,
        agentspec_agent: AgentSpecAgent,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> CrewAIAgent:
        crewai_agent = CrewAIAgentWithTracing(
            # We interpret the name as the `role` of the agent in CrewAI,
            # the description as the `backstory`, and the system prompt as the `goal`, as they are all required
            # This interpretation comes from the analysis of CrewAI Agent definition examples
            role=agentspec_agent.name,
            goal=agentspec_agent.system_prompt,
            backstory=agentspec_agent.description or "",
            llm=self.convert(
                agentspec_agent.llm_config,
                tool_registry=tool_registry,
                converted_components=converted_components,
            ),
            tools=[
                self.convert(
                    tool, tool_registry=tool_registry, converted_components=converted_components
                )
                for tool in agentspec_agent.tools
            ],
        )
        if not agentspec_agent.metadata:
            agentspec_agent.metadata = {}
        agentspec_agent.metadata["__crewai_agent_id__"] = str(crewai_agent.id)
        return crewai_agent
