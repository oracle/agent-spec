/**
 * FlowBuilder - builder pattern for constructing Agent Spec Flows.
 */
import type { ComponentWithIO } from "../component.js";
import type { Property } from "../property.js";
import { createStartNode } from "./nodes/start-node.js";
import { createEndNode } from "./nodes/end-node.js";
import {
  createBranchingNode,
  DEFAULT_BRANCH,
  DEFAULT_INPUT,
} from "./nodes/branching-node.js";
import {
  createControlFlowEdge,
  type ControlFlowEdge,
} from "./edges/control-flow-edge.js";
import {
  createDataFlowEdge,
  type DataFlowEdge,
} from "./edges/data-flow-edge.js";
import { createFlow, type Flow } from "./flow.js";

const DEFAULT_FLOW_NAME = "Flow";

type NodeLike = Record<string, unknown>;
type NodeOrName = NodeLike | string;

export class FlowBuilder {
  private nodes: Map<string, NodeLike> = new Map();
  private controlFlowConnections: ControlFlowEdge[] = [];
  private dataFlowConnections: DataFlowEdge[] = [];
  private _startNode?: NodeLike;
  private _conditionalEdgeCounter = 1;
  private _endNodeCounter = 1;

  /** Add a node to the flow */
  addNode(node: NodeLike): this {
    const name = node["name"] as string;
    if (this.nodes.has(name)) {
      throw new Error(`Node with name '${name}' already exists`);
    }
    this.nodes.set(name, node);
    return this;
  }

  /** Add a control flow edge */
  addEdge(
    sourceNode: NodeOrName | NodeOrName[],
    destNode: NodeOrName,
    fromBranch?: string | (string | null)[] | null,
    edgeName?: string,
  ): this {
    let startNodeList: NodeOrName[];
    let fromBranchList: (string | null | undefined)[];

    if (Array.isArray(sourceNode)) {
      startNodeList = sourceNode;
      fromBranchList = Array.isArray(fromBranch)
        ? fromBranch
        : new Array<string | null | undefined>(startNodeList.length).fill(
            fromBranch ?? undefined,
          );
    } else {
      if (Array.isArray(fromBranch)) {
        throw new Error(
          "A list was given for `fromBranch` but `sourceNode` is not a list of nodes.",
        );
      }
      startNodeList = [sourceNode];
      fromBranchList = [fromBranch ?? undefined];
    }

    if (startNodeList.length !== fromBranchList.length) {
      throw new Error("sourceNode and fromBranch must have the same length");
    }

    const destinationNode = this._getNode(destNode);

    for (let i = 0; i < startNodeList.length; i++) {
      const src = this._getNode(startNodeList[i]!);
      const branch = fromBranchList[i] ?? undefined;
      const srcName = src["name"] as string;
      const dstName = destinationNode["name"] as string;
      this.controlFlowConnections.push(
        createControlFlowEdge({
          name:
            edgeName ?? `control_edge_${srcName}_${dstName}_${branch ?? "null"}`,
          fromNode: src,
          toNode: destinationNode,
          fromBranch: branch,
        }),
      );
    }
    return this;
  }

  /** Add a data flow edge */
  addDataEdge(
    sourceNode: NodeOrName,
    destNode: NodeOrName,
    dataName: string | [string, string],
    edgeName?: string,
  ): this {
    const src = this._getNode(sourceNode);
    const dst = this._getNode(destNode);

    let sourceOutput: string;
    let destInput: string;
    if (Array.isArray(dataName)) {
      [sourceOutput, destInput] = dataName;
    } else {
      sourceOutput = dataName;
      destInput = dataName;
    }

    this.dataFlowConnections.push(
      createDataFlowEdge({
        name: edgeName ?? "data_flow_edge",
        sourceNode: src as ComponentWithIO,
        sourceOutput,
        destinationNode: dst as ComponentWithIO,
        destinationInput: destInput,
      }),
    );
    return this;
  }

  /** Add a sequence of nodes with control flow edges between them */
  addSequence(nodes: NodeLike[]): this {
    for (const node of nodes) {
      this.addNode(node);
    }
    if (nodes.length > 1) {
      for (let i = 0; i < nodes.length - 1; i++) {
        this.addEdge(nodes[i]!, nodes[i + 1]!);
      }
    }
    return this;
  }

  /** Add a conditional branching */
  addConditional(
    sourceNode: NodeOrName,
    sourceValue: string | [NodeOrName, string],
    destinationMap: Record<string, NodeOrName>,
    defaultDestination: NodeOrName,
    branchingNodeName?: string,
  ): this {
    const dataEdgeName = `DataEdgeForConditional_${this._conditionalEdgeCounter}`;
    const conditionalNodeName =
      branchingNodeName ?? `ConditionalNode_${this._conditionalEdgeCounter}`;
    this._conditionalEdgeCounter++;

    const destinationMapStr: Record<string, string> = {};
    for (const [k, v] of Object.entries(destinationMap)) {
      destinationMapStr[k] = typeof v === "string" ? v : (v["name"] as string);
    }

    // Prevent collision with default branch name (validate before mutating state)
    if (Object.values(destinationMapStr).includes(DEFAULT_BRANCH)) {
      throw new Error(
        `destinationMap cannot contain reserved branch label '${DEFAULT_BRANCH}'. ` +
          "Please use `defaultDestination` instead.",
      );
    }

    this.addNode(
      createBranchingNode({
        name: conditionalNodeName,
        mapping: destinationMapStr,
      }),
    );

    // Control flow edges
    this.addEdge(sourceNode, conditionalNodeName);
    for (const destNodeName of Object.values(destinationMapStr)) {
      this.addEdge(conditionalNodeName, destNodeName, destNodeName);
    }
    this.addEdge(conditionalNodeName, defaultDestination, DEFAULT_BRANCH);

    // Data flow edge for branching input
    if (sourceValue) {
      const srcNode = Array.isArray(sourceValue)
        ? sourceValue[0]
        : sourceNode;
      const srcVal = Array.isArray(sourceValue)
        ? sourceValue[1]
        : sourceValue;
      this.addDataEdge(
        srcNode,
        conditionalNodeName,
        [srcVal, DEFAULT_INPUT],
        dataEdgeName,
      );
    }

    return this;
  }

  /** Set the entry point of the flow (creates a StartNode) */
  setEntryPoint(node: NodeOrName, inputs?: Property[]): this {
    if (this._startNode !== undefined) {
      throw new Error(
        "Entry point already set; setEntryPoint cannot be called twice",
      );
    }
    const startNodeName = "StartNode";
    const startNode = createStartNode({ name: startNodeName, inputs });
    this._startNode = startNode;
    this.addNode(startNode);
    this.addEdge(startNodeName, node);
    return this;
  }

  /** Set finish points of the flow (creates EndNodes) */
  setFinishPoints(
    node: NodeOrName | NodeOrName[],
    outputs?: Property[] | (Property[] | null)[],
  ): this {
    const sourceNodeList = Array.isArray(node) ? node : [node];
    let outputsList: (Property[] | null | undefined)[];

    if (outputs === undefined || outputs === null) {
      outputsList = new Array<null>(sourceNodeList.length).fill(null);
    } else if (
      outputs.length > 0 &&
      !Array.isArray(outputs[0]) &&
      outputs[0] !== null &&
      typeof outputs[0] === "object" &&
      "jsonSchema" in (outputs[0] as Record<string, unknown>)
    ) {
      // Flat list of properties
      outputsList = [outputs as Property[]];
    } else {
      outputsList = outputs as (Property[] | null)[];
    }

    if (sourceNodeList.length !== outputsList.length) {
      throw new Error("Number of finish sources and outputs must match");
    }

    for (let i = 0; i < sourceNodeList.length; i++) {
      const endNodeName = `EndNode_${this._endNodeCounter}`;
      this._endNodeCounter++;
      const endOutputs = outputsList[i] ?? undefined;
      this.addNode(createEndNode({ name: endNodeName, outputs: endOutputs }));
      this.addEdge(sourceNodeList[i]!, endNodeName);
    }
    return this;
  }

  /** Build the Flow */
  build(name: string = DEFAULT_FLOW_NAME): Flow {
    let startNodeObj: NodeLike;
    if (this._startNode !== undefined) {
      startNodeObj = this._startNode;
    } else {
      const startNodes = [...this.nodes.values()].filter(
        (n) => n["componentType"] === "StartNode",
      );
      if (startNodes.length === 1) {
        startNodeObj = startNodes[0]!;
      } else if (startNodes.length > 1) {
        throw new Error("There cannot be more than one start node in a Flow");
      } else {
        throw new Error(
          "Missing start node, make sure to call `setEntryPoint`",
        );
      }
    }

    const hasEndNode = [...this.nodes.values()].some(
      (n) => n["componentType"] === "EndNode",
    );
    if (!hasEndNode) {
      throw new Error("Missing finish node");
    }

    return createFlow({
      name,
      startNode: startNodeObj,
      nodes: [...this.nodes.values()],
      controlFlowConnections: this.controlFlowConnections,
      dataFlowConnections:
        this.dataFlowConnections.length > 0
          ? this.dataFlowConnections
          : undefined,
    });
  }

  /** Build a linear (sequential) flow from a list of nodes */
  static buildLinearFlow(opts: {
    nodes: NodeLike[];
    name?: string;
    dataFlowEdges?: Array<
      | DataFlowEdge
      | [NodeOrName, NodeOrName, string]
      | [NodeOrName, NodeOrName, string, string]
    >;
    inputs?: Property[];
    outputs?: Property[];
  }): Flow {
    const nodes = opts.nodes;
    if (nodes.length === 0) {
      throw new Error("nodes list must not be empty");
    }
    if ((nodes[0]! as Record<string, unknown>)["componentType"] === "StartNode") {
      throw new Error(
        "It is not necessary to add a StartNode to the list of nodes",
      );
    }
    if (
      (nodes[nodes.length - 1]! as Record<string, unknown>)["componentType"] ===
      "EndNode"
    ) {
      throw new Error(
        "It is not necessary to add an EndNode to the list of nodes",
      );
    }

    const builder = new FlowBuilder().addSequence(nodes);

    if (opts.dataFlowEdges) {
      for (const edgeInfo of opts.dataFlowEdges) {
        if (Array.isArray(edgeInfo)) {
          if (edgeInfo.length === 3) {
            const [src, dst, dataName] = edgeInfo as [
              NodeOrName,
              NodeOrName,
              string,
            ];
            builder.addDataEdge(src, dst, dataName);
          } else {
            const [src, dst, srcIn, dstOut] = edgeInfo as [
              NodeOrName,
              NodeOrName,
              string,
              string,
            ];
            builder.addDataEdge(src, dst, [srcIn, dstOut]);
          }
        } else {
          const edge = edgeInfo as DataFlowEdge;
          builder.addDataEdge(
            edge.sourceNode,
            edge.destinationNode,
            [edge.sourceOutput, edge.destinationInput],
          );
        }
      }
    }

    const [inferredInputs, inferredOutputs] = inferLinearFlowInputsAndOutputs(
      opts.inputs ?? null,
      opts.outputs ?? null,
      nodes,
    );

    builder.setEntryPoint(nodes[0]!, inferredInputs);
    builder.setFinishPoints(nodes[nodes.length - 1]!, inferredOutputs);

    return builder.build(opts.name ?? DEFAULT_FLOW_NAME);
  }

  private _getNode(nodeOrName: NodeOrName): NodeLike {
    const name =
      typeof nodeOrName === "string"
        ? nodeOrName
        : (nodeOrName["name"] as string);
    const node = this.nodes.get(name);
    if (!node) {
      throw new Error(`Node with name '${name}' not found`);
    }
    return node;
  }
}

function inferLinearFlowInputsAndOutputs(
  inputs: Property[] | null,
  outputs: Property[] | null,
  nodes: NodeLike[],
): [Property[], Property[]] {
  let inferredInputs: Property[];
  if (inputs === null) {
    const producedNames = new Set<string>();
    const inputsMap = new Map<string, Property>();
    for (const node of nodes) {
      for (const inp of (node["inputs"] as Property[] | undefined) ?? []) {
        if (!producedNames.has(inp.title) && !inputsMap.has(inp.title)) {
          inputsMap.set(inp.title, inp);
        }
      }
      for (const out of (node["outputs"] as Property[] | undefined) ?? []) {
        producedNames.add(out.title);
      }
    }
    inferredInputs = [...inputsMap.values()];
  } else {
    inferredInputs = inputs;
  }

  let inferredOutputs: Property[];
  if (outputs === null) {
    const seenTitles = new Set<string>();
    const orderedOutputs: Property[] = [];
    for (const node of nodes) {
      for (const out of (node["outputs"] as Property[] | undefined) ?? []) {
        if (!seenTitles.has(out.title)) {
          seenTitles.add(out.title);
          orderedOutputs.push(out);
        }
      }
    }
    inferredOutputs = orderedOutputs;
  } else {
    inferredOutputs = outputs;
  }

  return [inferredInputs, inferredOutputs];
}
