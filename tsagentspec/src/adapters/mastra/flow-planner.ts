import type { Flow, Node } from "../../flows/index.js";
import {
  UnsupportedMastraFlowNodeError,
  UnsupportedMastraFlowShapeError,
} from "./errors.js";

export type MastraLinearFlowPlan = {
  flowId: string;
  nodeOrder: Node[];
  executableNodes: Array<Extract<Node, { componentType: "LlmNode" | "ToolNode" | "AgentNode" }>>;
  startNode: Extract<Node, { componentType: "StartNode" }>;
  endNode: Extract<Node, { componentType: "EndNode" }>;
};

const SUPPORTED_NODE_TYPES = new Set<string>([
  "StartNode",
  "LlmNode",
  "ToolNode",
  "AgentNode",
  "EndNode",
]);

export const planLinearMastraFlow = (flow: Flow): MastraLinearFlowPlan => {
  const nodes = flow.nodes as Node[];
  const startNodeRef = flow.startNode as Node;

  for (const node of nodes) {
    if (!SUPPORTED_NODE_TYPES.has(node.componentType)) {
      throw new UnsupportedMastraFlowNodeError(node.componentType);
    }
  }

  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const startNode = nodesById.get(startNodeRef.id);
  if (!startNode || startNode.componentType !== "StartNode") {
    throw new UnsupportedMastraFlowShapeError(
      "Linear Mastra flow requires a StartNode as the flow start node.",
    );
  }

  const outgoingByNodeId = new Map<string, typeof flow.controlFlowConnections>();
  for (const edge of flow.controlFlowConnections) {
    const fromNode = edge.fromNode as Node;
    const edges = outgoingByNodeId.get(fromNode.id) ?? [];
    edges.push(edge);
    outgoingByNodeId.set(fromNode.id, edges);
  }

  const nodeOrder: Node[] = [];
  const executableNodes: MastraLinearFlowPlan["executableNodes"] = [];
  const visited = new Set<string>();
  let current: Node = startNode;

  // Walk one `next` edge at a time. Anything branched, cyclic, or disconnected
  // is rejected so the converted workflow has the same shape as the source flow.
  while (true) {
    if (visited.has(current.id)) {
      throw new UnsupportedMastraFlowShapeError(
        `Linear Mastra flow cannot contain cycles. Revisited node '${current.name}'.`,
      );
    }
    visited.add(current.id);
    nodeOrder.push(current);

    if (isExecutableNode(current)) {
      executableNodes.push(current);
    }

    if (current.componentType === "EndNode") {
      break;
    }

    const outgoing = outgoingByNodeId.get(current.id) ?? [];
    if (outgoing.length !== 1) {
      throw new UnsupportedMastraFlowShapeError(
        `Linear Mastra flow requires exactly one outgoing edge from '${current.name}', found ${outgoing.length}.`,
      );
    }

    const [edge] = outgoing;
    if (edge!.fromBranch && edge!.fromBranch !== "next") {
      throw new UnsupportedMastraFlowShapeError(
        `Linear Mastra flow does not support branch '${edge!.fromBranch}' from '${current.name}'.`,
      );
    }

    const toNode = edge!.toNode as Node;
    const next = nodesById.get(toNode.id);
    if (!next) {
      throw new UnsupportedMastraFlowShapeError(
        `Flow edge '${edge!.name}' points to a node outside the flow.`,
      );
    }
    current = next;
  }

  if (visited.size !== nodes.length) {
    const unreachable = nodes
      .filter((node) => !visited.has(node.id))
      .map((node) => node.name)
      .sort();
    throw new UnsupportedMastraFlowShapeError(
      `Linear Mastra flow cannot contain disconnected or branched nodes: ${unreachable.join(", ")}.`,
    );
  }

  const endNode = current;
  if (endNode.componentType !== "EndNode") {
    throw new UnsupportedMastraFlowShapeError(
      "Linear Mastra flow must terminate at an EndNode.",
    );
  }

  return {
    flowId: flow.id,
    nodeOrder,
    executableNodes,
    startNode,
    endNode,
  };
};

const isExecutableNode = (
  node: Node,
): node is MastraLinearFlowPlan["executableNodes"][number] =>
  node.componentType === "LlmNode" ||
  node.componentType === "ToolNode" ||
  node.componentType === "AgentNode";
