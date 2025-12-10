# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import types
from typing import Any, Dict, List, Optional, Union, cast, get_args, get_origin

from pyagentspec.adapters.autogen._types import (
    AutogenAssistantAgent,
    AutogenBaseAgent,
    AutogenBaseTool,
    AutogenChatCompletionClient,
    AutogenComponent,
    AutogenFunctionTool,
    AutogenGraphFlow,
    AutogenOllamaChatCompletionClient,
    AutogenOpenAIChatCompletionClient,
)
from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.component import Component as AgentSpecComponent
from pyagentspec.flows.edges import ControlFlowEdge as AgentSpecControlFlowEdge
from pyagentspec.flows.edges import DataFlowEdge as AgentSpecDataFlowEdge
from pyagentspec.flows.flow import Flow as AgentSpecFlow
from pyagentspec.flows.node import Node as AgentSpecNode
from pyagentspec.flows.nodes import AgentNode as AgentSpecAgentNode
from pyagentspec.flows.nodes import BranchingNode as AgentSpecBranchingNode
from pyagentspec.flows.nodes import EndNode as AgentSpecEndNode
from pyagentspec.flows.nodes import StartNode as AgentSpecStartNode
from pyagentspec.flows.nodes import ToolNode as AgentSpecToolNode
from pyagentspec.llms import LlmConfig as AgentSpecLlmConfig
from pyagentspec.llms.ollamaconfig import OllamaConfig as AgentSpecOllamaModel
from pyagentspec.llms.openaiconfig import OpenAiConfig as AgentSpecOpenAiModel
from pyagentspec.llms.vllmconfig import VllmConfig as AgentSpecVllmModel
from pyagentspec.property import BooleanProperty as AgentSpecBooleanProperty
from pyagentspec.property import FloatProperty as AgentSpecFloatProperty
from pyagentspec.property import IntegerProperty as AgentSpecIntegerProperty
from pyagentspec.property import ListProperty as AgentSpecListProperty
from pyagentspec.property import NullProperty as AgentSpecNullProperty
from pyagentspec.property import ObjectProperty as AgentSpecObjectProperty
from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import StringProperty as AgentSpecStringProperty
from pyagentspec.property import UnionProperty as AgentSpecUnionProperty
from pyagentspec.tools import ServerTool as AgentSpecServerTool
from pyagentspec.tools import Tool as AgentSpecTool


class AutogenToAgentSpecConverter:
    """
    Provides methods to convert various types of Autogen components into their corresponding PyAgentSpec components.
    """

    def convert(
        self,
        autogen_component: Union[
            AutogenComponent[Any],
            AutogenBaseTool[Any, Any],
            AutogenChatCompletionClient,
            AutogenGraphFlow,
            AutogenBaseAgent,
        ],
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> AgentSpecComponent:
        """
        Convert an Autogen component to its corresponding PyAgentSpec component.

        Parameters:
        - autogen_component: The Autogen component to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecComponent
            The converted PyAgentSpec component.
        """

        if referenced_objects is None:
            referenced_objects = dict()

        # Reuse the same object multiple times in order to exploit the referencing system
        object_reference = _get_obj_reference(autogen_component)
        if object_reference in referenced_objects:
            return referenced_objects[object_reference]

        # If we did not find the object, we create it, and we record it in the referenced_objects registry
        agentspec_component: AgentSpecComponent
        if isinstance(autogen_component, AutogenChatCompletionClient):
            agentspec_component = self._llm_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        elif isinstance(autogen_component, AutogenBaseAgent):
            agentspec_component = self._agent_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        elif isinstance(autogen_component, AutogenBaseTool):
            agentspec_component = self._tool_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        elif isinstance(autogen_component, AutogenGraphFlow):
            agentspec_component = self._flow_convert_to_agentspec(
                autogen_component, referenced_objects
            )
        else:
            raise NotImplementedError(
                f"The autogen type '{autogen_component.__class__.__name__}' is not yet supported "
                f"for conversion. It is very easy to add support, you should do it!"
            )
        referenced_objects[object_reference] = agentspec_component
        return referenced_objects[object_reference]

    def _flow_convert_to_agentspec(
        self,
        autogen_flow: AutogenGraphFlow,
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
        generate_tool_snippets: bool = False,
    ) -> AgentSpecFlow:
        """
        Convert an AutoGen GraphFlow into a basic AgentSpec Flow.
        Names of inputs and outputs of the final AgentSpecFlow will have the same names as those of the original start and leaf nodes in the AutoGen flow.

        Current strategy
        ----------------
        1.  Each AutoGen participant becomes an AgentSpecAgentNode that wraps the
            underlying AgentSpecAgent produced by `self.convert`.
        2.  We create a synthetic StartNode that fans-out to all start vertices
            of the original graph, and a single EndNode that every leaf vertex
            connects to.
        3.  For each source vertex:
            - Collect edges from flow._graph.nodes[src_name].edges
            • condition_function (callable) -> handled as lambda-like conditional
            • condition (str) -> handled as string conditional
            • no condition and no condition_function -> unconditional
            - If the source has any conditional edge (callable or string), build a BranchingNode.
            • If there is at least one callable, insert a synthetic ServerTool + ToolNode that
                returns a branch label; wire src -> tool -> branch.
            • Map callable conditions to unique synthetic labels "callable_{src_name}_{idx}".
            • Map string conditions to their string values.
            • Control edges branch -> targets per label; data flows src -> targets.
            - Otherwise, for unconditional edges, wire src -> tgt directly.
        4. In case of branching conditions, method also prints a sketched template of the servertools to provide in the tool_registry with minimal adjustment needed to make it easier to run on runtimes.

        Returns:
        -------
        AgentSpecFlow
            The converted AgentSpecFlow from AutoGen to AgentSpec.

        """

        # -----------------------------------------------------------------
        # 0. Convenience handles to the AutoGen graph information
        # -----------------------------------------------------------------
        autogen_graph_dict = autogen_flow.dump_component().config["graph"]["nodes"]
        participant_by_name = {
            p.name: p for p in autogen_flow._participants  # pylint: disable=protected-access
        }

        # -----------------------------------------------------------------
        # 1. Convert participants → AgentSpecAgentNode instances
        # NOTE: autogen_flow._participants also contains the internal
        #       _StopAgent—but _StopAgent never appears in
        #       autogen_graph_dict["nodes"].  So we just iterate over the
        #       real graph vertices to avoid touching it.
        # -----------------------------------------------------------------
        agentspec_nodes = self._participants_convert_to_agentspec(
            autogen_graph_dict, participant_by_name, referenced_objects
        )

        # -----------------------------------------------------------------
        # 2. Synthetic START / END nodes
        # -----------------------------------------------------------------

        # END Node:
        end_node = self._create_synthetic_end_node(autogen_flow, agentspec_nodes)

        # START Node:
        start_node = self._create_synthetic_start_node(autogen_flow, agentspec_nodes)

        # -----------------------------------------------------------------
        # 3. Control-flow & data-flow edges
        # -----------------------------------------------------------------
        control_edges: List[AgentSpecControlFlowEdge] = []
        data_edges: List[AgentSpecDataFlowEdge] = []
        extra_nodes: list[AgentSpecNode] = []
        generated_branching_tool_snippets: List[str] = (
            []
        )  # Used for printing required servertools in synthetic ToolNodes
        generated_branching_tool_entries: List[tuple[str, str]] = (
            []
        )  # (tool_id, function_name) to print a single tool_registry with all required servertools

        # suffix used for start and end nodes to make sure we have distinct edges in case user employs those names.
        # Also suffix used to distinguish branches
        def _mirror_edges(
            src_node: AgentSpecNode,
            tgt_node: AgentSpecNode,
            suffix: str = "",
            create_control_flow_edge: bool = True,
        ) -> None:
            if create_control_flow_edge:
                cf_edge = AgentSpecControlFlowEdge(
                    name=f"{src_node.name}_to_{tgt_node.name}_{suffix}_cf",
                    from_node=src_node,
                    to_node=tgt_node,
                )
                control_edges.append(cf_edge)

            # Extract property names
            # Here we suppose of course that each AgentNode only has one single input and output
            source_output = src_node.outputs[0].title if src_node.outputs else ""
            destination_input = tgt_node.inputs[0].title if tgt_node.inputs else ""

            df_edge = AgentSpecDataFlowEdge(
                name=f"{src_node.name}_to_{tgt_node.name}_{suffix}_df",
                source_node=src_node,
                source_output=source_output,
                destination_node=tgt_node,
                destination_input=destination_input,
            )
            data_edges.append(df_edge)

        # 3.1 edges in the original graph
        # Walk every vertex in the AutoGen graph
        # Edges without condition cannot be mixed with other edges with conditions in AutoGen. Therefore, either 3.1.a or 3.1.b
        for src_name in autogen_graph_dict.keys():
            src_node = agentspec_nodes[src_name]

            # Read edges from the DiGraph node
            # Each edge has attributes: target, condition (str|None), condition_function (callable|None)
            digraph_node = autogen_flow._graph.nodes[src_name]
            edges = getattr(digraph_node, "edges", []) or []

            # edges with callable conditions
            callable_conditional_edges: list[dict[str, object]] = []
            # edges with string conditions
            string_conditional_edges: list[dict[str, str]] = []
            # edges without conditions
            unconditional_edges: list[dict[str, str]] = []

            for e in edges:
                tgt_name = getattr(e, "target", None)
                if not tgt_name:
                    continue
                cond = getattr(e, "condition", None)
                cond_fn = getattr(e, "condition_function", None)

                if cond_fn is not None and callable(cond_fn):
                    callable_conditional_edges.append(
                        {"target": tgt_name, "condition_function": cond_fn}
                    )
                elif isinstance(cond, str):
                    string_conditional_edges.append({"target": tgt_name, "condition": cond})
                else:
                    unconditional_edges.append({"target": tgt_name})

            has_any_conditional = bool(callable_conditional_edges or string_conditional_edges)
            has_callable = bool(callable_conditional_edges)

            # 3.1.a:  nodes that have at least one conditional edge
            # The created BranchingNode will route inputs based on the labels.
            # Our conversion also handles cases when string and callable conditions are mixed in the same source node.
            if has_any_conditional:
                if not src_node.outputs:
                    raise ValueError(f"Node {src_node.name} exposes no outputs")

                # Branch input is the source node's first output
                branch_input_prop = _untyped_text_property(src_node.outputs[0].title)

                # This must match the ToolNode/ServerTool input Property title so that frameworks such as WayFlow can bind kwargs
                branch_input_param_name = getattr(branch_input_prop, "title", None)
                if not branch_input_param_name:
                    branch_input_param_name = branch_input_prop.json_schema.get(
                        "title", "branch_input"
                    )

                # Prepare branch labels and mapping
                branch_labels_by_target: dict[str, str] = {}
                branch_labels: list[str] = []
                # For code-generation: (label, target) for callables; (condition, target) for strings
                callable_specs_for_template: List[tuple[str, str]] = []
                string_specs_for_template: List[tuple[str, str]] = []

                if has_callable:
                    for idx, e in enumerate(callable_conditional_edges, start=1):
                        tgt = str(e["target"])
                        label = f"callable_{src_name}_{idx}"
                        branch_labels_by_target[tgt] = label
                        branch_labels.append(label)
                        callable_specs_for_template.append((label, tgt))

                for e in string_conditional_edges:
                    tgt = e["target"]
                    label = e["condition"]
                    branch_labels_by_target[tgt] = label
                    branch_labels.append(label)
                    string_specs_for_template.append((label, tgt))

                # Create the BranchingNode (consumes a label and routes on it)
                branch_node = AgentSpecBranchingNode(
                    name=f"{src_name}_branch",
                    mapping={label: label for label in branch_labels},
                    inputs=[branch_input_prop],
                )
                extra_nodes.append(branch_node)

                # Generate and store function template for this source (for user to register)
                snippet = self._render_branching_tool_source(
                    src_name=src_name,
                    callable_specs=callable_specs_for_template,
                    string_specs=string_specs_for_template,
                    input_param_name=branch_input_param_name,
                )
                if generate_tool_snippets:
                    generated_branching_tool_snippets.append(snippet)

                # What execution-time code needs to provide in case of edge conditions:
                #   In your execution framework (e.g., WayFlow), you must register a Server tool for each branching tool:
                #   tool_registry key: branching_tool_{src_name}
                #   Signature of the servertool : def branching_tool_{src_name}(branch_input: str) -> str
                #   Behavior of the servertool: evaluate callables first; on first True return the callable’s label (callable_{src_name}_{idx}); otherwise, check string conditions and return the matching string; if nothing matches, return an empty string or any

                # Insert synthetic ServerTool + ToolNode per source that returns the selected branch label
                tool_id = f"branching_tool_{src_name}"
                branching_tool = AgentSpecServerTool(
                    id=tool_id,
                    name=tool_id,
                    description="synthetic servertool node to handle conditions of branching",
                    inputs=[branch_input_prop],
                    outputs=[branch_input_prop],  # output is the selected branch label
                )
                # Accumulate tool-id → function-name to print one unified tool registry later
                generated_branching_tool_entries.append((tool_id, f"branching_tool_{src_name}"))

                tool_node = AgentSpecToolNode(
                    name=f"tool_node_branching_{src_name}",
                    description="synthetic tool node to handle conditions of branching",
                    inputs=[branch_input_prop],
                    outputs=[branch_input_prop],
                    tool=branching_tool,
                )
                extra_nodes.append(tool_node)

                # Wiring: src → tool → branch
                _mirror_edges(src_node, tool_node, suffix="BRANCH_TOOL_IN")
                _mirror_edges(tool_node, branch_node, suffix="BRANCH_TOOL_OUT")

                # Control edges: branch → targets using computed labels
                for e in callable_conditional_edges:
                    tgt_name = str(e["target"])
                    tgt_node = agentspec_nodes[tgt_name]
                    branch_label = branch_labels_by_target[tgt_name]
                    control_edges.append(
                        AgentSpecControlFlowEdge(
                            name=f"{branch_node.name}_to_{tgt_node.name}_{branch_label}_cf",
                            from_node=branch_node,
                            from_branch=branch_label,
                            to_node=tgt_node,
                        )
                    )
                    # Data still flows from src → tgt
                    # Note: this passes the source node's output value intact to the target node to avoid interference during previous branching.
                    _mirror_edges(src_node, tgt_node, branch_label, create_control_flow_edge=False)

                for e in string_conditional_edges:
                    tgt_node = agentspec_nodes[e["target"]]
                    branch_label = branch_labels_by_target[e["target"]]
                    control_edges.append(
                        AgentSpecControlFlowEdge(
                            name=f"{branch_node.name}_to_{tgt_node.name}_{branch_label}_cf",
                            from_node=branch_node,
                            from_branch=branch_label,
                            to_node=tgt_node,
                        )
                    )
                    # Important: do not add unconditional src→tgt control edges for these targets,
                    # to avoid duplicate 'source_branch=next' control edges (WayFlow restriction).
                    _mirror_edges(src_node, tgt_node, branch_label, create_control_flow_edge=False)

                # AutoGen does not have a special conditional edge to go to end node, so we will always have this default branch which in principle should not conflict with other conditions.
                # Add control flow edge for default branch
                control_edges.append(
                    AgentSpecControlFlowEdge(
                        name=f"{branch_node.name}_to_{end_node.name}_DEFAULT_cf",
                        from_node=branch_node,
                        from_branch=AgentSpecBranchingNode.DEFAULT_BRANCH,
                        to_node=end_node,
                    )
                )

            # 3.1.b: unconditional edges (no condition with string or callable)
            for e in unconditional_edges:
                _mirror_edges(src_node, agentspec_nodes[e["target"]])

        # 3.2 fan-out from START
        for src in autogen_flow._graph.get_start_nodes():
            _mirror_edges(start_node, agentspec_nodes[src], "START")

        # 3.3 fan-in to END
        for leaf in autogen_flow._graph.get_leaf_nodes():
            _mirror_edges(agentspec_nodes[leaf], end_node, "END")

        # -----------------------------------------------------------------
        # 4. Assemble the AgentSpec Flow
        # -----------------------------------------------------------------
        all_nodes: list[AgentSpecNode] = [
            start_node,
            end_node,
            *agentspec_nodes.values(),
            *extra_nodes,
        ]

        flow = AgentSpecFlow(
            name=getattr(
                autogen_flow, "name", "Converted AutoGen GraphFlow"
            ),  # GraphFlow in old AutoGen versions like our current version doesn't support name and description attributes so default value will be used.
            start_node=start_node,
            nodes=all_nodes,
            control_flow_connections=control_edges,
            data_flow_connections=data_edges,
        )

        if generate_tool_snippets:
            # Print all generated function templates once (helps users easily register server tools in the tool registry at runtime)
            if generated_branching_tool_snippets:
                print("\n# ---- Generated ServerTool function templates for branching ----")
                for snippet in generated_branching_tool_snippets:
                    print(snippet)
                # Print a single unified tool_registry with all branching tools
                if generated_branching_tool_entries:
                    print("# Register in your runtime tool registry, e.g. ")
                    print("tool_registry = {")
                    for tool_id, func_name in generated_branching_tool_entries:
                        print(f'    "{tool_id}": {func_name},')
                    print("}")
                print("# ---- End of generated ServerTool templates ----\n")
                print("# Note: to disable this message, please set generate_tool_snippets to False")
        return flow

    def _create_synthetic_start_node(
        self,
        autogen_flow: AutogenGraphFlow,
        agentspec_nodes: Dict[str, "AgentSpecAgentNode"],
    ) -> "AgentSpecStartNode":
        """
        2. Synthetic START node.

        - Finds all start agent nodes (nodes that start the graph).
        - Aggregates and deduplicates all their inputs.
        """
        start_agent_nodes = [
            agentspec_nodes[name] for name in autogen_flow._graph.get_start_nodes()
        ]
        if not start_agent_nodes:
            raise RuntimeError("No start nodes found in AutoGen flow!")
        # Aggregate and deduplicate all their inputs
        start_inputs: List[AgentSpecProperty] = []
        for node in start_agent_nodes:
            if node.inputs:
                for input_prop in node.inputs:
                    if all(input_prop.title != o.title for o in start_inputs):
                        start_inputs.append(input_prop)
        return AgentSpecStartNode(name="start", inputs=start_inputs)

    def _create_synthetic_end_node(
        self,
        autogen_flow: AutogenGraphFlow,
        agentspec_nodes: Dict[str, "AgentSpecAgentNode"],
    ) -> "AgentSpecEndNode":
        # Find leaf agent node outputs (agent nodes that end the graph)
        leaf_agent_nodes = [agentspec_nodes[name] for name in autogen_flow._graph.get_leaf_nodes()]
        if not leaf_agent_nodes:
            raise RuntimeError("No leaf nodes found in AutoGen flow!")

        # Flow ends when these finish. Aggregate all their outputs
        # (If more than one leaf node, collect all, or if only one, just use that.)
        end_outputs_by_title: Dict[str, AgentSpecProperty] = {}
        for node in leaf_agent_nodes:
            if node.outputs:
                for output_property in node.outputs:
                    # Avoid duplicates if there are multiple leaf nodes
                    if output_property.title not in end_outputs_by_title:
                        end_outputs_by_title[output_property.title] = output_property
        # Convert back to a list for AgentSpecEndNode
        end_outputs: List[AgentSpecProperty] = list(end_outputs_by_title.values())

        return AgentSpecEndNode(name="end", outputs=end_outputs)

    def _participants_convert_to_agentspec(
        self,
        autogen_graph_dict: Dict[str, Any],
        participant_by_name: Dict[str, Any],
        referenced_objects: Optional[Dict[str, AgentSpecComponent]] = None,
    ) -> Dict[str, AgentSpecAgentNode]:
        """
        Converts AutoGen participants into a mapping of AgentSpecAgentNode instances.

        Parameters:
            autogen_graph_dict: Dictionary of the graph's node names.
            participant_by_name: Mapping from participant names to AutoGen agent objects.
            referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
            Dict[str, AgentSpecAgentNode]: Map of node name to AgentSpecAgentNode.
        """
        agentspec_nodes: Dict[str, AgentSpecAgentNode] = {}
        for name in autogen_graph_dict.keys():
            ag_participant = participant_by_name[name]
            # a) Convert the AutoGen agent to an AgentSpecAgent
            agentspec_agent = cast(
                AgentSpecAgent,
                self.convert(cast(AutogenBaseAgent, ag_participant), referenced_objects),
            )
            # b) Wrap it in an AgentSpecAgentNode
            agentspec_nodes[name] = AgentSpecAgentNode(
                name=name,
                description=agentspec_agent.description,
                agent=agentspec_agent,
            )
        return agentspec_nodes

    def _llm_convert_to_agentspec(
        self,
        autogen_llm: AutogenChatCompletionClient,
        referenced_objects: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecLlmConfig:
        """
        Convert an AutogenChatCompletionClient to an AgentSpecLlmConfig.

        Parameters:
        - autogen_llm: The Autogen LLM to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecLlmConfig
            The converted AgentSpecLlmConfig.

        Raises:
        ------
        ValueError
            If the type of LLM is unsupported.
        """
        if isinstance(autogen_llm, AutogenOllamaChatCompletionClient):
            _autogen_component = autogen_llm.dump_component()
            return AgentSpecOllamaModel(
                name=_autogen_component.config["model"],
                model_id=_autogen_component.config["model"],
                url=_autogen_component.config["host"],
            )
        elif isinstance(autogen_llm, AutogenOpenAIChatCompletionClient):
            _autogen_component = autogen_llm.dump_component()
            if "base_url" in _autogen_component.config and _autogen_component.config["base_url"]:
                return AgentSpecVllmModel(
                    name=_autogen_component.config["model"],
                    model_id=_autogen_component.config["model"],
                    url=_autogen_component.config["base_url"],
                    metadata={
                        "model_info": json.dumps(_autogen_component.config.get("model_info", {})),
                    },
                )
            return AgentSpecOpenAiModel(
                name=_autogen_component.config["model"],
                model_id=_autogen_component.config["model"],
            )
        raise ValueError(f"Unsupported type of LLM in agentspec: {type(autogen_llm)}")

    def _agentspec_input_property_from_type(
        self, prop_val: Dict[str, Any], title: str, description: str
    ) -> AgentSpecProperty:
        if prop_val["type"] == "string":
            return AgentSpecStringProperty(title=title, description=description)
        elif prop_val["type"] == "integer":
            return AgentSpecIntegerProperty(title=title, description=description)
        elif prop_val["type"] == "boolean":
            return AgentSpecBooleanProperty(title=title, description=description)
        elif prop_val["type"] == "number":
            return AgentSpecFloatProperty(title=title, description=description)
        elif prop_val["type"] == "null":
            return AgentSpecNullProperty(title=title, description=description)
        else:
            raise NotImplementedError(f"Unsupported type of output property: {prop_val['type']}")

    def _agentspec_output_property_from_type(
        self, _type: Any, title: str = "Output"
    ) -> AgentSpecProperty:
        """Map a Python/typing type to a corresponding AgentSpec/pyagentspec Property."""
        # Handle built-ins and simple types
        type_name = getattr(_type, "__name__", str(_type))
        if type_name == "str":
            return AgentSpecStringProperty(title=title)
        elif type_name == "int":
            return AgentSpecIntegerProperty(title=title)
        elif type_name == "float":
            return AgentSpecFloatProperty(title=title)
        elif type_name == "bool":
            return AgentSpecBooleanProperty(title=title)
        elif type_name == "NoneType":
            return AgentSpecNullProperty(title=title)
        raise NotImplementedError(f"Unsupported type of output property: {type_name}")

    def make_agentspec_output_property(
        self, _type: Any, title: str = "Output"
    ) -> AgentSpecProperty:
        origin = get_origin(_type)
        args = get_args(_type)
        if (origin is Union) or (hasattr(types, "UnionType") and origin is types.UnionType):
            union_properties = [
                self.make_agentspec_output_property(arg, title=title) for arg in args
            ]
            return AgentSpecUnionProperty(title=title, any_of=union_properties)
        elif origin is list:
            inner_type = args[0] if args else Any
            item_property = self.make_agentspec_output_property(inner_type, title=title)
            return AgentSpecListProperty(title=title, item_type=item_property)
        elif origin is dict:
            object_properties = {
                prop_name: self.make_agentspec_output_property(prop_type, title=prop_name)
                for prop_name, prop_type in getattr(_type, "__annotations__", {}).items()
            }
            return AgentSpecObjectProperty(title=title, properties=object_properties)
        else:
            return self._agentspec_output_property_from_type(_type, title=title)

    def make_agentspec_input_property(
        self, prop_val: Dict[str, Any], title: str, description: str
    ) -> AgentSpecProperty:

        if "anyOf" in prop_val:
            union_items = prop_val.get("anyOf") or []
            union_properties = [
                self.make_agentspec_input_property(item, title=title, description=description)
                for item in union_items
            ]
            return AgentSpecUnionProperty(
                title=title, description=description, any_of=union_properties
            )
        elif prop_val["type"] == "array":
            item_property = self.make_agentspec_input_property(
                prop_val["items"], title=title, description=description
            )
            return AgentSpecListProperty(
                title=title, description=description, item_type=item_property
            )
        elif prop_val["type"] == "object":
            props = prop_val.get("properties", {})
            dict_properties = {
                k: self.make_agentspec_input_property(
                    v, title=k, description=v.get("description", "")
                )
                for k, v in props.items()
            }
            return AgentSpecObjectProperty(
                title=title, description=description, properties=dict_properties
            )
        else:
            return self._agentspec_input_property_from_type(
                prop_val, title=title, description=description
            )

    def _render_branching_tool_source(
        self,
        src_name: str,
        callable_specs: List[tuple[str, str]],  # list of (callable_label, target_name)
        string_specs: List[tuple[str, str]],  # list of (condition_string, target_name)
        input_param_name: str,  # MUST match ToolNode/ServerTool input property title
    ) -> str:
        """
        Return a Python function string for the synthetic ServerTool 'branching_tool_{src_name}', created for branching.

        - Function argument name matches the ToolNode input property title.
        - callables are placeholders; each TODO includes the intended target node name.
        - String conditions check substring inclusion and indicate their target.
        - Returning "" falls through to the BranchingNode default branch.
        """
        lines: List[str] = []
        func_name = f"branching_tool_{src_name}"
        arg_name = input_param_name

        lines.append(f"def {func_name}({arg_name}: str) -> str:")
        if not callable_specs and not string_specs:
            lines.append("    # No conditions found; fall back to default branch")
            lines.append('    return ""')
            return "\n".join(lines)

        # callable placeholders first (user has to implement them)
        for idx, (label, tgt_name) in enumerate(callable_specs, start=1):
            lines.append(
                f"    # TODO: implement original callable condition #{idx} for source '{src_name}' "
                f"that routes to target '{tgt_name}'"
            )
            lines.append(f"    def callable_{src_name}_{idx}(msg_text: str) -> bool: ...")
            lines.append(f"    if callable_{src_name}_{idx}({arg_name}):")
            lines.append(f'        return "{label}"')

        # String conditions next
        for cond, tgt_name in string_specs:
            safe_cond = cond.replace('"', '\\"')
            lines.append(f"    # If this matches, route to target '{tgt_name}'")
            lines.append(f'    if "{safe_cond}" in {arg_name}:')
            lines.append(f'        return "{safe_cond}"')

        # Default
        lines.append('    return ""  # default → BranchingNode.DEFAULT_BRANCH')
        lines.append("")
        return "\n".join(lines)

    def _tool_convert_to_agentspec(
        self,
        autogen_tool: AutogenBaseTool[Any, Any],
        referenced_objects: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecTool:
        """
        Convert an AutogenBaseTool to an AgentSpecTool.

        Parameters:
        - autogen_tool: The Autogen tool to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecTool
            The converted AgentSpecTool.

        Raises:
        ------
        ValueError
            If the type of tool is unsupported.
        """
        if isinstance(autogen_tool, AutogenFunctionTool):
            _schema = autogen_tool.schema
            _schema_properties = _schema["parameters"]["properties"]
            _return_type = autogen_tool._signature.return_annotation
            _inputs = []
            for prop_val in _schema_properties.values():
                _input = self.make_agentspec_input_property(
                    prop_val=prop_val,
                    title=prop_val["title"],
                    description=prop_val["description"],
                )
                _inputs.append(_input)

            _outputs = []
            _output = self.make_agentspec_output_property(_return_type)
            _outputs.append(_output)

            return AgentSpecServerTool(
                name=_schema["name"],
                description=_schema["description"],
                inputs=_inputs,
                outputs=_outputs,
            )
        raise ValueError(f"Unsupported type of Tool in AgentSpec: {type(autogen_tool)}")

    def _agent_convert_to_agentspec(
        self,
        autogen_agent: AutogenBaseAgent,
        referenced_objects: Optional[Dict[str, Any]] = None,
    ) -> AgentSpecAgent:
        """
        Convert an AutogenBaseAgent to an AgentSpecAgent.

        Parameters:
        - autogen_agent: The Autogen agent to be converted.
        - referenced_objects: A dictionary to keep track of already converted objects.

        Returns:
        -------
        AgentSpecAgent
            The converted AgentSpecAgent.

        Raises:
        ------
        ValueError
            If the type of agent is unsupported.
        """
        if isinstance(autogen_agent, AutogenAssistantAgent):
            _autogen_component = autogen_agent.dump_component()
            agentspec_llm_config = self.convert(autogen_agent._model_client, referenced_objects)
            agentspec_tools = [
                t
                for t in (self.convert(_tool, referenced_objects) for _tool in autogen_agent._tools)
                if isinstance(t, AgentSpecTool)
            ]

            # New system prompt with name of the input property provided to handle case of agents inside flows.
            # if not provided in system prompt, AgentSpecAgent will complain about inputs.
            # Note: pay close attention to how the tools’ return values are formatted—especially if another agent expects a specific schema.
            #       In particular, if output_content_type_format or tool_call_summary_format/tool_call_summary_formatter are used.
            # .      tool_call_summary_formatter is intended for in-code use only, and cannot be saved or restored via configuration files, so it is not handled.
            system_prompt_text = (
                (_autogen_component.config["system_message"] or "")
                + ". This is the user input: {{"
                + _autogen_component.config["name"]
                + "_input}}"
            )

            return AgentSpecAgent(
                name=_autogen_component.config["name"],
                description=_autogen_component.config["description"],
                llm_config=cast(AgentSpecLlmConfig, agentspec_llm_config),
                system_prompt=system_prompt_text,
                tools=agentspec_tools,
                inputs=[_untyped_text_property(_autogen_component.config["name"] + "_input")],
                outputs=[_untyped_text_property(_autogen_component.config["name"] + "_output")],
            )
        raise ValueError(f"Unsupported type of agent in AgentSpec: {type(autogen_agent)}")


def _get_obj_reference(obj: Any) -> str:
    return f"{obj.__class__.__name__.lower()}/{id(obj)}"


def _untyped_text_property(title: str) -> AgentSpecProperty:
    """Return a minimal Property that represents a free-form text message."""
    returned_property = AgentSpecProperty(
        json_schema={
            "title": title,
            "description": "Untyped textual payload coming from AutoGen",
            "type": "string",
            "default": "",
        }
    )
    return returned_property
