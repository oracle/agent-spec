/**
 * Flow - a sequence of operations defined by nodes and edges.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { ComponentWithIOSchema } from "../component.js";
import { ControlFlowEdgeSchema, type ControlFlowEdge } from "./edges/control-flow-edge.js";
import { DataFlowEdgeSchema, type DataFlowEdge } from "./edges/data-flow-edge.js";
import { LazyNodeRef, registerFlowSchema } from "./lazy-schemas.js";

export const FlowSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("Flow"),
  startNode: LazyNodeRef,
  nodes: z.array(LazyNodeRef),
  controlFlowConnections: z.array(ControlFlowEdgeSchema),
  dataFlowConnections: z.array(DataFlowEdgeSchema).optional(),
});

registerFlowSchema(FlowSchema);

export type Flow = z.infer<typeof FlowSchema>;

/** Get EndNodes from the nodes list */
function getEndNodes(
  nodes: Record<string, unknown>[],
): Record<string, unknown>[] {
  return nodes.filter((n) => n["componentType"] === "EndNode");
}

/** Infer inputs from the start node */
function inferFlowInputs(
  startNode: Record<string, unknown>,
): Property[] {
  return (startNode["inputs"] as Property[] | undefined) ?? [];
}

/** Infer outputs from EndNodes: outputs present in ALL EndNodes */
function inferFlowOutputs(
  nodes: Record<string, unknown>[],
): Property[] {
  const endNodes = getEndNodes(nodes);
  if (endNodes.length === 0) return [];

  const endNodeOutputs: Property[] = [];
  for (const endNode of endNodes) {
    for (const output of (endNode["outputs"] as Property[] | undefined) ?? []) {
      endNodeOutputs.push(output);
    }
  }

  const flowOutputsByName: Record<string, Property> = {};
  for (const output of endNodeOutputs) {
    const outputName = output.jsonSchema["title"] as string;
    if (outputName in flowOutputsByName) continue;
    // Check that output name appears in all end nodes
    const inAllEndNodes = endNodes.every((endNode) =>
      ((endNode["outputs"] as Property[] | undefined) ?? []).some(
        (o) => (o.jsonSchema["title"] as string) === outputName,
      ),
    );
    if (inAllEndNodes) {
      flowOutputsByName[outputName] = output;
    }
  }
  return Object.values(flowOutputsByName);
}

/** Validate flow graph invariants before schema parsing */
function validateFlowInvariants(opts: {
  startNode: Record<string, unknown>;
  nodes: Record<string, unknown>[];
  controlFlowConnections: ControlFlowEdge[];
  dataFlowConnections?: DataFlowEdge[];
}): void {
  const { startNode, nodes, controlFlowConnections, dataFlowConnections } = opts;

  // 1. Exactly one StartNode
  const startNodes = nodes.filter((n) => n["componentType"] === "StartNode");
  if (startNodes.length !== 1) {
    throw new Error(
      `A Flow should be composed of exactly one StartNode, contains ${startNodes.length}.\n` +
        "Please check for missing or duplicated nodes.",
    );
  }

  // 2. StartNode matches opts.startNode
  if (startNodes[0]!["id"] !== startNode["id"]) {
    throw new Error(
      "The ``start_node`` node is not matching the start node from the " +
        `list of nodes in the flow \`\`nodes\`\` (start node was '${startNode["name"]}', ` +
        `found '${startNodes[0]!["name"]}' in \`\`nodes\`\`).`,
    );
  }

  // 3. StartNode has exactly one outgoing control flow edge
  const startOutgoing = controlFlowConnections.filter(
    (edge) => (edge.fromNode as Record<string, unknown>)["id"] === startNode["id"],
  );
  if (startOutgoing.length !== 1) {
    throw new Error(
      "The ``start_node`` should have exactly one outgoing control flow edge, " +
        `found ${startOutgoing.length}. Please check the list of control flow edges.`,
    );
  }

  // 4. No incoming control flow edges to StartNode
  const startIncoming = controlFlowConnections.filter(
    (edge) => (edge.toNode as Record<string, unknown>)["componentType"] === "StartNode",
  );
  if (startIncoming.length > 0) {
    const names = startIncoming.map((e) => e.name);
    throw new Error(
      "Transitions to StartNode is not accepted. Please check the " +
        `following control flow edges: \n${JSON.stringify(names)}`,
    );
  }

  // 5. At least one EndNode
  const endNodes = nodes.filter((n) => n["componentType"] === "EndNode");
  if (endNodes.length === 0) {
    throw new Error(
      "A Flow should be composed of at least one EndNode but " +
        "didn't find any in ``nodes``. Please make sure to add EndNode(s) to the flow.",
    );
  }

  // 6. Every EndNode has at least one incoming control flow edge
  for (const endNode of endNodes) {
    const incoming = controlFlowConnections.filter(
      (edge) => (edge.toNode as Record<string, unknown>)["id"] === endNode["id"],
    );
    if (incoming.length === 0) {
      throw new Error(
        "Found an end node without any incoming control flow edge, " +
          `which is not permitted (node is '${endNode["name"]}'). Please check the control flow edges.`,
      );
    }
  }

  // 7. No outgoing control flow edges from EndNode
  const endOutgoing = controlFlowConnections.filter(
    (edge) => (edge.fromNode as Record<string, unknown>)["componentType"] === "EndNode",
  );
  if (endOutgoing.length > 0) {
    const names = endOutgoing.map((e) => e.name);
    throw new Error(
      "Transitions from EndNode is not accepted. Please check the " +
        `following control flow connections: \n${JSON.stringify(names)}`,
    );
  }

  // 8. All control edge fromNode/toNode exist in nodes
  const nodeIds = new Set(nodes.map((n) => n["id"] as string));
  for (const edge of controlFlowConnections) {
    const fromId = (edge.fromNode as Record<string, unknown>)["id"] as string;
    const fromName = (edge.fromNode as Record<string, unknown>)["name"] as string;
    if (!nodeIds.has(fromId)) {
      throw new Error(
        `A control flow edge was defined, but the flow does not contain the source node '${fromName}'`,
      );
    }
    const toId = (edge.toNode as Record<string, unknown>)["id"] as string;
    const toName = (edge.toNode as Record<string, unknown>)["name"] as string;
    if (!nodeIds.has(toId)) {
      throw new Error(
        `A control flow edge was defined, but the flow does not contain the destination node '${toName}'`,
      );
    }
  }

  // 9. All data edge sourceNode/destinationNode exist in nodes
  for (const edge of dataFlowConnections ?? []) {
    const srcId = (edge.sourceNode as Record<string, unknown>)["id"] as string;
    const srcName = (edge.sourceNode as Record<string, unknown>)["name"] as string;
    if (!nodeIds.has(srcId)) {
      throw new Error(
        `A data flow edge was defined, but the flow does not contain the source node '${srcName}'`,
      );
    }
    const destId = (edge.destinationNode as Record<string, unknown>)["id"] as string;
    const destName = (edge.destinationNode as Record<string, unknown>)["name"] as string;
    if (!nodeIds.has(destId)) {
      throw new Error(
        `A data flow edge was defined, but the flow does not contain the destination node '${destName}'`,
      );
    }
  }
}

export function createFlow(opts: {
  name: string;
  startNode: Record<string, unknown>;
  nodes: Record<string, unknown>[];
  controlFlowConnections: ControlFlowEdge[];
  dataFlowConnections?: DataFlowEdge[];
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): Flow {
  validateFlowInvariants(opts);
  const inputs = opts.inputs ?? inferFlowInputs(opts.startNode);
  const outputs = opts.outputs ?? inferFlowOutputs(opts.nodes);

  return Object.freeze(
    FlowSchema.parse({
      ...opts,
      inputs,
      outputs,
      componentType: "Flow" as const,
    }),
  );
}
