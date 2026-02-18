/**
 * DataFlowEdge - defines data flow between node outputs and inputs.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../../component.js";
import { propertyIsCastableTo, type Property } from "../../property.js";

const NodeRef = z.record(z.unknown());

export const DataFlowEdgeSchema = ComponentBaseSchema.extend({
  componentType: z.literal("DataFlowEdge"),
  sourceNode: NodeRef,
  sourceOutput: z.string(),
  destinationNode: NodeRef,
  destinationInput: z.string(),
});

export type DataFlowEdge = z.infer<typeof DataFlowEdgeSchema>;

function findPropertyByTitle(
  properties: unknown[] | undefined,
  title: string,
): Property | undefined {
  if (!Array.isArray(properties)) return undefined;
  return (properties as Property[]).find((p) => p.title === title);
}

export function createDataFlowEdge(opts: {
  name: string;
  sourceNode: Record<string, unknown>;
  sourceOutput: string;
  destinationNode: Record<string, unknown>;
  destinationInput: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): DataFlowEdge {
  const sourceOutputs = opts.sourceNode["outputs"] as unknown[] | undefined;
  const sourceProperty = findPropertyByTitle(sourceOutputs, opts.sourceOutput);
  if (sourceOutputs && sourceOutputs.length > 0 && !sourceProperty) {
    const sourceName = (opts.sourceNode["name"] as string) ?? "unknown";
    throw new Error(
      `Flow data connection named \`${opts.name}\` is connected to a property ` +
        `named \`${opts.sourceOutput}\` of the source node \`${sourceName}\`, ` +
        `but the node does not have any output property with that name.`,
    );
  }

  const destInputs = opts.destinationNode["inputs"] as unknown[] | undefined;
  const destProperty = findPropertyByTitle(destInputs, opts.destinationInput);
  if (destInputs && destInputs.length > 0 && !destProperty) {
    const destName = (opts.destinationNode["name"] as string) ?? "unknown";
    throw new Error(
      `Flow data connection named \`${opts.name}\` is connected to a property ` +
        `named \`${opts.destinationInput}\` of the destination node \`${destName}\`, ` +
        `but the node does not have any input property with that name.`,
    );
  }

  if (sourceProperty && destProperty) {
    if (!propertyIsCastableTo(sourceProperty, destProperty)) {
      throw new Error(
        `Flow data connection named \`${opts.name}\` connects two properties ` +
          `with incompatible types: \`${opts.sourceOutput}\` and \`${opts.destinationInput}\`.`,
      );
    }
  }

  return Object.freeze(
    DataFlowEdgeSchema.parse({
      ...opts,
      componentType: "DataFlowEdge" as const,
    }),
  );
}
