# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from types import CellType
from typing import Any, Dict, List, Optional, cast

from langchain_core.runnables import RunnableBinding
from langchain_ollama import ChatOllama
from langchain_openai.chat_models import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph, StateNodeSpec
from langgraph_agentspec_adapter._agentspec_converter_flow import (
    _langgraph_graph_convert_to_agentspec,
)
from langgraph_agentspec_adapter._types import LangGraphComponent, LangGraphLlmConfig

from pyagentspec import Property
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms import OllamaConfig as AgentSpecOllamaConfig
from pyagentspec.llms import VllmConfig as AgentSpecVllmConfig
from pyagentspec.tools import ServerTool
from pyagentspec.tools import Tool as AgentSpecTool


class LangGraphToAgentSpecConverter:
    def convert(
        self,
        langgraph_component: LangGraphComponent,
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        """Convert the given LangGraph component object into the corresponding PyAgentSpec component"""
        if referenced_objects is None:
            referenced_objects = {}

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = self._get_obj_reference(langgraph_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        referenced_objects[object_reference] = self._convert(
            langgraph_component=langgraph_component,
            referenced_objects=referenced_objects,
        )
        return referenced_objects[object_reference]

    def _convert(
        self,
        langgraph_component: LangGraphComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecComponent:
        agentspec_component: Optional[AgentSpecComponent] = None
        if self._is_react_agent(langgraph_component):
            agentspec_component = self._langgraph_agent_convert_to_agentspec(
                langgraph_component, referenced_objects
            )
        else:
            agentspec_component = _langgraph_graph_convert_to_agentspec(
                self, langgraph_component, referenced_objects
            )

        if agentspec_component is None:
            raise NotImplementedError(f"Conversion for {langgraph_component} not implemented yet")

        return agentspec_component

    def _is_react_agent(
        self,
        langgraph_component: LangGraphComponent,
    ) -> bool:
        if isinstance(langgraph_component, CompiledStateGraph):
            langgraph_component = langgraph_component.builder
        # Creating an agent with the `create_react_agent` creates a node with the key "agent"
        node = langgraph_component.nodes.get("agent")
        return node is not None and hasattr(node.runnable, "get_graph")

    def _extract_llm_config_from_runnables_closures(
        self, agent_node: StateNodeSpec[Any]
    ) -> LangGraphLlmConfig:
        nodes = cast(Any, agent_node.runnable).get_graph().nodes

        # The graph contains three nodes:
        # - call_model_input node
        # - the call_model Runnable node
        # - a call_model_output node
        # We can get the data that we want from the call_model Runnable node
        call_model_node = next(node for node in nodes.values() if node.name == "call_model")

        # Get the Runnable from the node
        runnable: Any = call_model_node.data

        # Extract variables that have been closed over in the `create_react_agent` function execution
        # Because the data related to the model's configuration has been wrapped in a runnable,
        # and isn't stored in a class's attributes for example
        closure: tuple[CellType, ...] = runnable.func.__closure__

        # Extract the instance of RunnableBinding which contains relevant information for the react agent
        model = next(
            cl.cell_contents.last
            for cl in closure
            if hasattr(cl.cell_contents, "last")
            and isinstance(cl.cell_contents.last, RunnableBinding)
        )
        tools = self._langgraph_tools_to_agentspec_tools(model.kwargs["tools"])

        if isinstance(model, RunnableBinding):
            model = model.bound  # type: ignore
        if isinstance(model, ChatOpenAI):
            model_type = "vllm"
            model_name = model.model_name
            base_url = model.openai_api_base
        elif isinstance(model, ChatOllama):
            model_type = "ollama"
            model_name = model.model
            base_url = model.base_url
        else:
            raise ValueError(
                f"The LLM instance provided is of an unsupported type `{type(model)}`."
            )

        return LangGraphLlmConfig(
            model_type=model_type,
            model_name=model_name,
            base_url=base_url or "",
            tools=tools,
        )

    def _extract_prompt_from_react_agent_node(
        self, langgraph_agent_node: StateNodeSpec[Any]
    ) -> str:
        # The agent_node's runnable corresponds to the `call_model` function, that contains the prompt somewhere
        call_model_function = langgraph_agent_node.runnable.func  # type: ignore
        # We get the cell contents of the last element of the `call_model` function closure,
        # which should contain the sequence of actions performed by the runnable (it's a runnable sequence)
        call_model_runnable_sequence = call_model_function.__closure__[-1].cell_contents
        # The first element of the function related to this runnable sequence is a Prompt (a runnable as well)
        # Getting the first element of its function closure will take us to the SystemMessage
        if call_model_runnable_sequence.first.func.__closure__ is None:
            # No system prompt was provided, we return empty string
            return ""
        system_message = call_model_runnable_sequence.first.func.__closure__[0].cell_contents
        # This system message contains the prompt we need
        return str(system_message.content)

    def _langgraph_tools_to_agentspec_tools(
        self, tools: List[Dict[str, Any]]
    ) -> List[AgentSpecTool]:
        return [
            ServerTool(
                name=tool["function"]["name"],
                description=tool["function"]["description"],
                inputs=[Property(json_schema=tool["function"]["parameters"])],
            )
            for tool in tools
        ]

    def _build_agentspec_llm_from_config(
        self, langgraph_llm_config: LangGraphLlmConfig
    ) -> AgentSpecLlmConfig:
        if langgraph_llm_config.model_type == "ollama":
            return AgentSpecOllamaConfig(
                name=langgraph_llm_config.model_name,
                url=langgraph_llm_config.base_url,
                model_id=langgraph_llm_config.model_name,
            )
        elif langgraph_llm_config.model_type == "vllm":
            return AgentSpecVllmConfig(
                name=langgraph_llm_config.model_name,
                url=langgraph_llm_config.base_url,
                model_id=langgraph_llm_config.model_name,
            )
        raise ValueError(
            f"The LLM instance provided is of an unsupported type `{langgraph_llm_config.model_type}`."
        )

    def _langgraph_agent_convert_to_agentspec(
        self,
        langgraph_component: LangGraphComponent,
        referenced_objects: Dict[str, AgentSpecComponent],
    ) -> AgentSpecAgent:
        if isinstance(langgraph_component, CompiledStateGraph):
            agent_name = langgraph_component.get_name()
        else:
            agent_name = "LangGraph Agent"
        if isinstance(langgraph_component, CompiledStateGraph):
            langgraph_component = langgraph_component.builder
        agent_node = langgraph_component.nodes["agent"]
        llm_config = self._extract_llm_config_from_runnables_closures(agent_node)
        return AgentSpecAgent(
            name=agent_name,
            llm_config=self._build_agentspec_llm_from_config(llm_config),
            system_prompt=self._extract_prompt_from_react_agent_node(agent_node),
            tools=llm_config.tools,
        )

    def _get_obj_reference(self, obj: Any) -> str:
        return f"{obj.__class__.__name__.lower()}/{id(obj)}"
