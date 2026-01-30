# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import inspect
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
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
    CrewAIFlow,
    CrewAILlm,
    CrewAIStructuredTool,
    CrewAITool,
    FlowState,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
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
        elif isinstance(crewai_component, CrewAIFlow):
            agentspec_component = self._flow_convert_to_agentspec(
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

    def _flow_convert_to_agentspec(
        self, crewai_flow: CrewAIFlow[FlowState], referenced_objects: Dict[str, Any]
    ) -> AgentSpecFlow:

        nodes: Dict[str, AgentSpecNode] = {}

        # Create a ToolNode for each method (i.e. node) in the flow
        methods_by_name = getattr(crewai_flow, "_methods", {})
        start_method_names = getattr(crewai_flow, "_start_methods", [])
        for method_name in methods_by_name.keys():
            method_callable = methods_by_name[method_name]

            # CrewAI nodes are basically python functions with no requirements with
            # respect to defining their inputs and outputs (compared with e.g. AgentSpec).
            # One workaround to infer these is to look at the function's signature.
            signature = inspect.signature(method_callable)

            # Create input properties for nodes:
            # add one input property for each parameter in the method's signature
            parameters = [p for p in signature.parameters.values() if p.name != "self"]
            node_inputs = [AgentSpecProperty(title=p.name) for p in parameters]

            # Create output properties for nodes:
            # if there is a return value annotation, add a single output property
            # (we don't try to handle multiple outputs here since that's not supported in CrewAI)
            return_annotation = signature.return_annotation
            has_output = not (
                return_annotation is inspect.Signature.empty or return_annotation is None
            )
            node_outputs = [AgentSpecProperty(title=f"{method_name}_output")] if has_output else []

            tool = AgentSpecServerTool(
                name=method_name,
                description=f"Converted CrewAI flow method '{method_name}'",
                inputs=node_inputs,
                outputs=node_outputs,
            )
            node = AgentSpecToolNode(name=method_name, tool=tool)
            nodes[method_name] = node
            referenced_objects[method_name] = node

        # Start node with inferred properties
        start_node_properties = [
            property
            for start_method in start_method_names
            for property in (nodes[start_method].inputs or [])
        ]
        start_node = AgentSpecStartNode(
            name="START", inputs=start_node_properties, outputs=start_node_properties
        )
        nodes[start_node.name] = start_node
        referenced_objects[start_node.name] = start_node

        control_flow_edges: list[ControlFlowEdge] = []
        data_flow_edges: list[DataFlowEdge] = []

        # Branching is currently not supported, meaning that there should only be one start method
        if len(start_method_names) == 0:
            raise ValueError("Start methods are required but none were found.")
        elif len(start_method_names) > 1:
            raise NotImplementedError("Flows with multiple start methods are not yet supported.")

        # Connect START to the start method
        start_method = start_method_names[0]
        control_flow_edges, data_flow_edges = self._add_start_edges(
            start_node,
            nodes[start_method],
            control_flow_edges,
            data_flow_edges,
        )

        # CrewAI flows define their connections (data/control) by using @listen decorators.
        # In the flow's internals, this is defined in the _listeners attribute
        # and essentially tells which are the methods that trigger the current one.
        # We use this to build edges in the converted flow.
        listeners = getattr(crewai_flow, "_listeners", {})

        for listener_name, condition in listeners.items():
            triggers, has_branching = self._extract_triggers_from_condition(condition)
            if has_branching:
                raise NotImplementedError(
                    "Flows with branching ('AND' and 'OR' operators) are not yet supported. "
                    f"Got node {listener_name} with triggers {', '.join(triggers)}"
                )
            for trigger in triggers:
                if trigger in getattr(crewai_flow, "_methods", {}):
                    control_flow_edges, data_flow_edges = self._add_listener_edges(
                        nodes[trigger],
                        nodes[listener_name],
                        control_flow_edges,
                        data_flow_edges,
                    )

        # End node with inferred properties
        has_outgoing_edges: set[str] = set(
            edge.from_node.name for edge in control_flow_edges if edge.from_node.name != "END"
        )
        end_methods = [
            method_name
            for method_name in nodes
            if method_name not in ("START", "END") and method_name not in has_outgoing_edges
        ]
        end_node_properties = [
            property for end_method in end_methods for property in (nodes[end_method].outputs or [])
        ]
        end_node = AgentSpecEndNode(
            name="END", inputs=end_node_properties, outputs=end_node_properties
        )
        nodes[end_node.name] = end_node
        referenced_objects[end_node.name] = end_node

        # Connect END to all end methods
        for end_method in end_methods:
            control_flow_edges, data_flow_edges = self._add_end_edges(
                nodes[end_method],
                end_node,
                control_flow_edges,
                data_flow_edges,
            )

        return AgentSpecFlow(
            name=(crewai_flow.name or crewai_flow.__class__.__name__),
            start_node=start_node,
            nodes=list(nodes.values()),
            control_flow_connections=control_flow_edges,
            data_flow_connections=data_flow_edges,
        )

    def _add_start_edges(
        self,
        start_node: AgentSpecNode,
        destination_node: AgentSpecNode,
        control_flow_edges: List[ControlFlowEdge],
        data_flow_edges: List[DataFlowEdge],
    ) -> Tuple[List[ControlFlowEdge], List[DataFlowEdge]]:
        control_flow_edges.append(
            ControlFlowEdge(
                name=f"START_to_{destination_node.name}_control_edge",
                from_node=start_node,
                to_node=destination_node,
            )
        )
        start_node_outputs = start_node.outputs or []
        start_node_output_property_names = [property.title for property in start_node_outputs]
        destination_node_inputs = destination_node.inputs or []
        for property in destination_node_inputs:
            if property.title in start_node_output_property_names:
                data_flow_edges.append(
                    DataFlowEdge(
                        name=f"START_to_{destination_node.name}_data_edge",
                        source_node=start_node,
                        destination_node=destination_node,
                        source_output=property.title,
                        destination_input=property.title,
                    )
                )
        return control_flow_edges, data_flow_edges

    def _add_listener_edges(
        self,
        trigger_node: AgentSpecNode,
        listener_node: AgentSpecNode,
        control_flow_edges: List[ControlFlowEdge],
        data_flow_edges: List[DataFlowEdge],
    ) -> Tuple[List[ControlFlowEdge], List[DataFlowEdge]]:
        control_flow_edges.append(
            ControlFlowEdge(
                name=f"{trigger_node.name}_to_{listener_node.name}_control_edge",
                from_node=trigger_node,
                to_node=listener_node,
            )
        )
        trigger_node_outputs = trigger_node.outputs or []
        listener_node_inputs = listener_node.inputs or []

        # CrewAI flows don't handle passing multiple inputs/outputs as method parameters
        if len(trigger_node_outputs) > 1:
            raise ValueError(
                "Flow methods should not have more than 1 output. "
                f"Got method {trigger_node.name} with outputs: {trigger_node_outputs}"
            )
        if len(listener_node_inputs) > 1:
            raise ValueError(
                "Flow methods should not have more than 1 input. "
                f"Got method {listener_node.name} with outputs: {listener_node_inputs}"
            )
        if len(trigger_node_outputs) == 1 and len(listener_node_inputs) == 1:
            data_flow_edges.append(
                DataFlowEdge(
                    name=f"{trigger_node.name}_to_{listener_node.name}_data_edge",
                    source_node=trigger_node,
                    destination_node=listener_node,
                    source_output=trigger_node_outputs[0].title,
                    destination_input=listener_node_inputs[0].title,
                )
            )
        return control_flow_edges, data_flow_edges

    def _add_end_edges(
        self,
        source_node: AgentSpecNode,
        end_node: AgentSpecNode,
        control_flow_edges: List[ControlFlowEdge],
        data_flow_edges: List[DataFlowEdge],
    ) -> Tuple[List[ControlFlowEdge], List[DataFlowEdge]]:
        control_flow_edges.append(
            ControlFlowEdge(
                name=f"{source_node.name}_to_END_control_edge",
                from_node=source_node,
                to_node=end_node,
            )
        )
        source_node_outputs = source_node.outputs or []
        end_node_inputs = end_node.inputs or []
        end_node_input_property_names = [property.title for property in end_node_inputs]
        for property in source_node_outputs:
            if property.title in end_node_input_property_names:
                data_flow_edges.append(
                    DataFlowEdge(
                        name=f"{source_node.name}_to_END_data_edge",
                        source_node=source_node,
                        destination_node=end_node,
                        source_output=property.title,
                        destination_input=property.title,
                    )
                )
        return control_flow_edges, data_flow_edges

    def _extract_triggers_from_condition(self, condition: Any) -> Tuple[set[str], bool]:
        """
        Extract flat trigger names from CrewAI listener condition.
        """
        has_branching = False
        triggers: set[str] = set()

        def _is_branching_condition(condition_type: Any, methods: Any) -> bool:
            return (str(condition_type).upper() in ("AND", "OR")) and len(methods) > 1

        # Simple tuple form: (condition_type, methods)
        if isinstance(condition, tuple) and len(condition) == 2:
            condition_type, methods = condition
            for method in methods or []:
                triggers.add(str(method))
            return triggers, _is_branching_condition(condition_type, methods)

        # Dict form: {"type": "OR"/"AND", "methods": [...] } or {"type": ..., "conditions": [...]}
        if isinstance(condition, dict):
            condition_type = str(condition.get("type", "OR")).upper()
            if "methods" in condition:
                methods = condition.get("methods", [])
                for method in methods:
                    triggers.add(str(method))
                return triggers, _is_branching_condition(condition_type, methods)
            if "conditions" in condition:
                subconditions = condition.get("conditions", [])
                has_branching = _is_branching_condition(condition_type, subconditions)
                for subcondition in subconditions:
                    if isinstance(subcondition, dict):
                        subtriggers, sub_has_branching = self._extract_triggers_from_condition(
                            subcondition
                        )
                        triggers |= subtriggers
                        has_branching = has_branching or sub_has_branching
                    else:
                        triggers.add(str(subcondition))
                return triggers, has_branching

        # Direct string method/label
        if isinstance(condition, str):
            triggers.add(condition)
            return triggers, has_branching

        return triggers, has_branching
