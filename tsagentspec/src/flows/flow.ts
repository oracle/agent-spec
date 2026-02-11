/**
 * Flow - a sequence of operations defined by nodes and edges.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { ComponentWithIOSchema } from "../component.js";
import { ControlFlowEdgeSchema, type ControlFlowEdge } from "./edges/control-flow-edge.js";
import { DataFlowEdgeSchema, type DataFlowEdge } from "./edges/data-flow-edge.js";

const NodeRef = z.record(z.unknown());

export const FlowSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("Flow"),
  startNode: NodeRef,
  nodes: z.array(NodeRef),
  controlFlowConnections: z.array(ControlFlowEdgeSchema),
  dataFlowConnections: z.array(DataFlowEdgeSchema).optional(),
});

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
