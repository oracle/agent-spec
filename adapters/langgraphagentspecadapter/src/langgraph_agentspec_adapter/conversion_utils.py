# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Callable, Dict

from langgraph.graph import add_messages
from langgraph.graph.state import RunnableConfig
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore


def convert_nodes_to_registry(
    nodes: Dict[str, object],
    config: RunnableConfig,
    store: BaseStore | None = None,
) -> Dict[str, Callable]:
    """
    Utility function to convert nodes into an AgentSpec compatible tool registry

    Parameters
    ----------
        nodes:
            Tool registry containing functions or runnables
        config:
            Configuration for a runnable
        store:
            Persistent key-value store

    Returns
    -------
        Tool registry with Callables that accept state as sole input
    """
    return {
        name: _convert_node_to_registry_tool(node, config, store) for name, node in nodes.items()
    }


def _convert_node_to_registry_tool(
    node: object,
    config: RunnableConfig,
    store: BaseStore | None = None,
) -> Callable:
    """
    Convert node into a function compatible with an AgentSpec node generated from LangGraph

    Parameters
    ----------
        node:
            The function or runnable this node will run
        config:
            Configuration for a runnable
        store:
            Persistent key-value store

    Returns
    -------
        A Callable that can be run with state as sole input
    """
    # This wrapper function simplifies the signature
    # of the tools to contain only a state parameter
    # that matches the resulting AgentSpec configuration

    if config is None:
        raise ValueError("A configuration is needed to support features such as ClientTools")

    # The wrapper function replicates the behavior of LangGraph
    # when it comes to posting messages to the state
    def wrapper(func):
        def outer(state):
            output = func(state)
            if isinstance(output, dict) and "messages" in output:
                output["messages"] = add_messages(state["messages"], output["messages"])
            return output

        return outer

    match node:
        case ToolNode() as tool_node:

            def func(state):
                return tool_node._func(state, config, store=store)

            return wrapper(func)
        case node if callable(node):
            return wrapper(node)
        case unsupported_node:
            raise NotImplementedError(
                f"Provided node type: {type(unsupported_node)} is not supported"
            )
