# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import uuid
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel

from pyagentspec.adapters.crewai._types import (
    CrewAIAgent,
    CrewAIBaseTool,
    CrewAILlm,
    CrewAIStructuredTool,
    CrewAITool,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import LlmGenerationConfig as AgentSpecLlmGenerationConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaicompatibleconfig import (
    OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig,
)
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.llms.vllmconfig import VllmConfig as AgentSpecVllmModel
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool


def generate_id() -> str:
    return str(uuid.uuid4())


def _get_obj_reference(obj: Any) -> str:
    return f"{obj.__class__.__name__.lower()}/{id(obj)}"


def _pydantic_model_to_properties_list(model: Type[BaseModel]) -> List[AgentSpecProperty]:
    json_schema = model.model_json_schema()
    for property_name, property_json_schema in json_schema["properties"].items():
        property_json_schema["title"] = property_name
    return [
        AgentSpecProperty(json_schema=property_json_schema)
        for property_name, property_json_schema in json_schema["properties"].items()
    ]


def _python_type_to_jsonschema(py_type: Any) -> Dict[str, Any]:
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
    elif origin is list or origin is List:
        return {"type": "array", "items": _python_type_to_jsonschema(args[0])}
    elif origin is dict or origin is Dict:
        return {"type": "object"}
    elif origin is Union:
        return {"anyOf": [_python_type_to_jsonschema(a) for a in args if a is not type(None)]}
    else:
        return {}


def _get_return_type_json_schema_from_function_reference(
    func: Callable[..., Any],
) -> Dict[str, Any]:
    hints = get_type_hints(func)
    return _python_type_to_jsonschema(hints.get("return", str))


class CrewAIToAgentSpecConverter:

    def convert(
        self,
        crewai_component: Any,
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        """Convert the given CrewAI component object into the corresponding PyAgentSpec component"""

        if referenced_objects is None:
            referenced_objects = dict()

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = _get_obj_reference(crewai_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        agentspec_component: AgentSpecComponent
        if isinstance(crewai_component, CrewAILlm):
            agentspec_component = self._llm_convert_to_agentspec(
                crewai_component, referenced_objects
            )
        elif isinstance(crewai_component, CrewAIAgent):
            agentspec_component = self._agent_convert_to_agentspec(
                crewai_component, referenced_objects
            )
        elif isinstance(crewai_component, CrewAIBaseTool):
            agentspec_component = self._tool_convert_to_agentspec(
                crewai_component, referenced_objects
            )
        else:
            raise NotImplementedError(
                f"The crewai type '{crewai_component.__class__.__name__}' is not yet supported "
                f"for conversion. Please contact the AgentSpec team."
            )
        referenced_objects[object_reference] = agentspec_component
        return referenced_objects[object_reference]

    def _llm_convert_to_agentspec(
        self, crewai_llm: CrewAILlm, referenced_objects: Dict[str, Any]
    ) -> AgentSpecLlmConfig:
        model_provider, model_id = crewai_llm.model.split("/", 1)
        max_tokens = int(crewai_llm.max_tokens) if crewai_llm.max_tokens is not None else None
        default_generation_parameters = AgentSpecLlmGenerationConfig(
            temperature=crewai_llm.temperature,
            top_p=crewai_llm.top_p,
            max_tokens=max_tokens,
        )
        if model_provider == "ollama":
            if crewai_llm.base_url is None:
                raise ValueError("Ollama LLM configuration requires a non-null base_url")
            return AgentSpecOllamaModel(
                name=crewai_llm.model,
                model_id=model_id,
                url=crewai_llm.base_url,
                default_generation_parameters=default_generation_parameters,
            )
        elif model_provider == "hosted_vllm":
            if crewai_llm.api_base is None:
                raise ValueError("VLLM LLM configuration requires a non-null api_base")
            return AgentSpecVllmModel(
                name=crewai_llm.model,
                model_id=model_id,
                url=crewai_llm.api_base.replace("/v1", ""),
                default_generation_parameters=default_generation_parameters,
            )
        elif model_provider == "openai":
            if crewai_llm.api_base is not None:
                return AgentSpecOpenAiCompatibleConfig(
                    name=crewai_llm.model,
                    model_id=model_id,
                    url=crewai_llm.api_base.replace("/v1", ""),
                    default_generation_parameters=default_generation_parameters,
                )
            return AgentSpecOpenAiConfig(
                name=crewai_llm.model,
                model_id=model_id,
                default_generation_parameters=default_generation_parameters,
            )

        raise ValueError(f"Unsupported type of LLM in Agent Spec: {model_provider}")

    def _tool_convert_to_agentspec(
        self, crewai_tool: CrewAIBaseTool, referenced_objects: Dict[str, Any]
    ) -> AgentSpecTool:
        # We do our best to infer the output type
        if isinstance(crewai_tool, (CrewAIStructuredTool, CrewAITool)):
            # StructuredTool has the `func` attribute that contains the function
            output_json_schema = _get_return_type_json_schema_from_function_reference(
                crewai_tool.func
            )
        else:
            # Otherwise the CrewAI Tools are supposed to implement the `_run` method
            output_json_schema = _get_return_type_json_schema_from_function_reference(
                crewai_tool._run
            )
        # There seem to be no counterparts for client tools and remote tools in CrewAI at the moment
        return AgentSpecServerTool(
            name=crewai_tool.name,
            description=crewai_tool.description,
            inputs=_pydantic_model_to_properties_list(crewai_tool.args_schema),
            outputs=[AgentSpecProperty(title="result", json_schema=output_json_schema)],
        )

    def _agent_convert_to_agentspec(
        self, crewai_agent: CrewAIAgent, referenced_objects: Dict[str, Any]
    ) -> AgentSpecAgent:
        return AgentSpecAgent(
            id=str(crewai_agent.id),
            name=crewai_agent.role,
            description=crewai_agent.backstory,
            system_prompt=crewai_agent.goal,
            llm_config=cast(
                AgentSpecLlmConfig,
                self.convert(
                    crewai_agent.llm,
                    referenced_objects=referenced_objects,
                ),
            ),
            tools=[
                cast(AgentSpecTool, self.convert(tool, referenced_objects=referenced_objects))
                for tool in (crewai_agent.tools or [])
            ],
        )
