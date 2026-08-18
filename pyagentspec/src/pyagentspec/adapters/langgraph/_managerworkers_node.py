# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Runs a ``ManagerWorkers`` as a flow step.

``AgentSpecToLangGraphConverter._agent_node_convert_to_langgraph`` selects
:class:`ManagerWorkersNodeExecutor` when the node's agent is a ``ManagerWorkers``,
so :class:`~pyagentspec.adapters.langgraph._node_execution.AgentNodeExecutor` keeps
the plain-Agent behavior only.
"""

from typing import Any, Dict, List, Optional, Tuple

from pyagentspec.adapters._utils import render_template
from pyagentspec.adapters.langgraph._node_execution import AgentNodeExecutor
from pyagentspec.adapters.langgraph._types import (
    Checkpointer,
    CompiledStateGraph,
    ExecuteOutput,
    LangGraphTool,
    Messages,
    NodeExecutionDetails,
    RunnableConfig,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.managerworkers import ManagerWorkers as AgentSpecManagerWorkers


class ManagerWorkersNodeExecutor(AgentNodeExecutor):
    """Executes an ``AgentNode`` whose agent is a ``ManagerWorkers``.

    The hierarchical graph runs over ``MessagesState``, which can carry neither
    structured inputs inward nor a ``structured_response`` outward. Inputs are
    therefore rendered into the group-manager's system prompt before compiling, and
    the manager's final message is the node's single string output.
    """

    def __init__(
        self,
        node: AgentSpecAgentNode,
        tool_registry: Dict[str, "LangGraphTool"],
        converted_components: Dict[str, Any],
        checkpointer: Optional[Checkpointer],
        config: RunnableConfig,
        middleware: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(
            node, tool_registry, converted_components, checkpointer, config, middleware
        )
        if not isinstance(node.agent, AgentSpecManagerWorkers):
            raise TypeError(
                "ManagerWorkersNodeExecutor requires an AgentNode holding a ManagerWorkers"
            )
        self._manager_workers: AgentSpecManagerWorkers = node.agent
        # Anything but a single string output cannot be honored (see class docstring);
        # raising here fails at conversion time rather than mid-run.
        outputs = node.outputs or []
        if outputs and (len(outputs) != 1 or outputs[0].type != "string"):
            raise NotImplementedError(
                "A ManagerWorkers flow step supports a single string output; "
                f"node `{node.name}` declares {[o.title for o in outputs]}."
            )

    def _create_manager_workers_with_given_input_values(
        self, inputs: Dict[str, Any]
    ) -> CompiledStateGraph[Any, Any]:
        """Compile the ``ManagerWorkers`` with the node inputs rendered into the
        group-manager's ``system_prompt`` and the satisfied ports dropped.

        Cached by rendered prompt, the same key
        :meth:`AgentNodeExecutor._create_react_agent_with_given_input_values` uses.
        Calling the private converter entry point is deliberate, mirroring the react
        path: the public ``convert`` caches by component id, which would collapse the
        differently-rendered copies (all sharing the original's id) into one graph.
        """
        from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

        converter = AgentSpecToLangGraphConverter()
        component = self._manager_workers
        entry_agent = component.group_manager
        if not isinstance(entry_agent, AgentSpecAgent):
            # Nothing to render or cache; the converter owns the error for this case.
            return converter._manager_workers_convert_to_langgraph(
                component, **self._conversion_kwargs()
            )

        system_prompt = render_template(entry_agent.system_prompt, inputs)
        if system_prompt not in self._agents_cache:
            rendered = component.model_copy(
                update={
                    "group_manager": entry_agent.model_copy(
                        update={"system_prompt": system_prompt, "inputs": []}
                    ),
                    "inputs": [],
                }
            )
            self._agents_cache[system_prompt] = converter._manager_workers_convert_to_langgraph(
                rendered, **self._conversion_kwargs()
            )
        return self._agents_cache[system_prompt]

    def _prepare_agent_and_inputs(
        self, inputs: Dict[str, Any], messages: Messages
    ) -> Tuple[CompiledStateGraph[Any, Any], Dict[str, Any]]:
        # Inputs were baked into the group-manager's prompt, so this graph runs on
        # messages alone rather than the react-agent's remaining_steps state.
        graph = self._create_manager_workers_with_given_input_values(inputs)
        return graph, {"messages": self._with_driving_message(messages)}

    def _format_agent_result(self, result: Dict[str, Any]) -> ExecuteOutput:
        node_outputs = self.node.outputs
        if not node_outputs:
            return super()._format_agent_result(result)
        # __init__ already rejected any shape but a single string output.
        return {node_outputs[0].title: result["messages"][-1].content}, NodeExecutionDetails()
