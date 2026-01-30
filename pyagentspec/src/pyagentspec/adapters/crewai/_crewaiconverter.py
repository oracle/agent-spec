# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, List, Optional, cast

from pyagentspec import Component as AgentSpecComponent
from pyagentspec.adapters._tools_common import _create_remote_tool_func
from pyagentspec.adapters._utils import create_pydantic_model_from_properties
from pyagentspec.adapters.crewai._node_execution import NodeExecutor
from pyagentspec.adapters.crewai._types import (
    ControlFlow,
    CrewAIAgent,
    CrewAIBaseTool,
    CrewAIFlow,
    CrewAIListenNode,
    CrewAILlm,
    CrewAIOrOperator,
    CrewAIServerToolType,
    CrewAIStartNode,
    CrewAITool,
    FlowState,
)
from pyagentspec.adapters.crewai.tracing import CrewAIAgentWithTracing
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import InputMessageNode as AgentSpecInputMessageNode
from pyagentspec.flows.nodes import LlmNode as AgentSpecLlmNode
from pyagentspec.flows.nodes import OutputMessageNode as AgentSpecOutputMessageNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms import OpenAiCompatibleConfig as AgentSpecOpenAiCompatibleConfig
from pyagentspec.llms import OpenAiConfig as AgentSpecOpenAiConfig
from pyagentspec.llms import VllmConfig as AgentSpecVllmModel
from pyagentspec.tools import ClientTool as AgentSpecClientTool
from pyagentspec.tools import RemoteTool as AgentSpecRemoteTool
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool


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
            elif isinstance(agentspec_component, AgentSpecFlow):
                crewai_component = self._flow_convert_to_crewai(
                    agentspec_component, tool_registry, converted_components
                )
            elif isinstance(agentspec_component, AgentSpecNode):
                crewai_component = self._node_convert_to_crewai(
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

    def _flow_convert_to_crewai(
        self,
        flow: AgentSpecFlow,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Dict[str, Any],
    ) -> CrewAIFlow[FlowState]:

        node_executors: Dict[str, NodeExecutor] = {
            node.id: self.convert(
                node,
                tool_registry=tool_registry,
                converted_components=converted_components,
            )
            for node in (flow.nodes or [])
        }

        # Data flow edges (handled by node executors)
        for data_flow_edge in flow.data_flow_connections or []:
            node_executors[data_flow_edge.source_node.id].attach_edge(data_flow_edge)
            node_executors[data_flow_edge.destination_node.id].attach_edge(data_flow_edge)

        # Initialize the class namespace for the CrewAI Flow
        crewai_class_namespace: Dict[str, Any] = {}
        crewai_class_namespace["name"] = flow.name or "ConvertedCrewAIFlow"

        # Prepare node executors to be decorated
        for _node_id, node_executor in node_executors.items():
            node_wrapper = node_executor.get_node_wrapper()
            node_wrapper.__name__ = node_executor.node.name
            crewai_class_namespace[node_wrapper.__name__] = node_wrapper

        # Apply the @start decorator to the AgentSpec start node
        start_node_name = flow.start_node.name
        crewai_class_namespace[start_node_name] = CrewAIStartNode()(
            crewai_class_namespace[start_node_name]
        )

        # Apply the @listen decorator to destination nodes
        control_flow = self._create_control_flow(flow.control_flow_connections)

        listen_conditions: Dict[str, List[str]] = {}
        for source_node_id, control_flow_mapping in control_flow.items():
            for _branch_label, destination_node_id in control_flow_mapping.items():
                source_node_name = node_executors[source_node_id].node.name
                destination_node_name = node_executors[destination_node_id].node.name
                listen_conditions.setdefault(destination_node_name, []).append(source_node_name)

        for listen_node_name, conditions in listen_conditions.items():
            conditions_union = CrewAIOrOperator(*conditions)
            crewai_class_namespace[listen_node_name] = CrewAIListenNode(conditions_union)(
                crewai_class_namespace[listen_node_name]
            )

        # Create the Flow subclass and return an instance of it
        ConvertedCrewAIFlow = cast(
            type[CrewAIFlow[FlowState]],
            type(
                "ConvertedCrewAIFlow",
                (CrewAIFlow,),
                crewai_class_namespace,
            ),
        )
        return ConvertedCrewAIFlow()

    def _create_control_flow(self, control_flow_connections: List[ControlFlowEdge]) -> ControlFlow:
        control_flow: ControlFlow = {}
        for control_flow_edge in control_flow_connections:
            source_node_id = control_flow_edge.from_node.id
            if source_node_id not in control_flow:
                control_flow[source_node_id] = {}

            branch_name = control_flow_edge.from_branch or AgentSpecNode.DEFAULT_NEXT_BRANCH
            control_flow[source_node_id][branch_name] = control_flow_edge.to_node.id

        return control_flow

    def _node_convert_to_crewai(
        self,
        node: AgentSpecNode,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutor:
        if isinstance(node, AgentSpecStartNode):
            return self._start_node_convert_to_crewai(node)
        elif isinstance(node, AgentSpecEndNode):
            return self._end_node_convert_to_crewai(node)
        elif isinstance(node, AgentSpecToolNode):
            return self._tool_node_convert_to_crewai(node, tool_registry, converted_components)
        elif isinstance(node, AgentSpecLlmNode):
            return self._llm_node_convert_to_crewai(node, tool_registry, converted_components)
        elif isinstance(node, AgentSpecInputMessageNode):
            return self._input_message_node_convert_to_crewai(node)
        elif isinstance(node, AgentSpecOutputMessageNode):
            return self._output_message_node_convert_to_crewai(node)
        else:
            raise NotImplementedError(
                f"The AgentSpec component of type {type(node)} is not yet supported for conversion"
            )

    def _start_node_convert_to_crewai(self, node: AgentSpecStartNode) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import StartNodeExecutor

        return StartNodeExecutor(node)

    def _end_node_convert_to_crewai(self, node: AgentSpecEndNode) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import EndNodeExecutor

        return EndNodeExecutor(node)

    def _tool_node_convert_to_crewai(
        self,
        node: AgentSpecToolNode,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]],
    ) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import ToolNodeExecutor

        tool = self.convert(
            node.tool, tool_registry=tool_registry, converted_components=converted_components
        )
        return ToolNodeExecutor(node, tool)

    def _llm_node_convert_to_crewai(
        self,
        node: AgentSpecLlmNode,
        tool_registry: Dict[str, CrewAIServerToolType],
        converted_components: Optional[Dict[str, Any]],
    ) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import LlmNodeExecutor

        llm = self.convert(
            node.llm_config, tool_registry=tool_registry, converted_components=converted_components
        )
        return LlmNodeExecutor(node, llm)

    def _input_message_node_convert_to_crewai(
        self, node: AgentSpecInputMessageNode
    ) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import InputMessageNodeExecutor

        return InputMessageNodeExecutor(node)

    def _output_message_node_convert_to_crewai(
        self, node: AgentSpecOutputMessageNode
    ) -> "NodeExecutor":
        from pyagentspec.adapters.crewai._node_execution import OutputMessageNodeExecutor

        return OutputMessageNodeExecutor(node)

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
                    args_schema=create_pydantic_model_from_properties(
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
                args_schema=create_pydantic_model_from_properties(
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
            args_schema=create_pydantic_model_from_properties(
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
