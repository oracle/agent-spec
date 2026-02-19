/**
 * DataFlowEdge - defines data flow between node outputs and inputs.
 */
import { z } from "zod";
import { ComponentBaseSchema, type ComponentWithIO } from "../../component.js";
import { propertyIsCastableTo, type Property } from "../../property.js";
import { LazyNodeRef } from "../lazy-schemas.js";

export const DataFlowEdgeSchema = ComponentBaseSchema.extend({
  componentType: z.literal("DataFlowEdge"),
  sourceNode: LazyNodeRef,
  sourceOutput: z.string(),
  destinationNode: LazyNodeRef,
  destinationInput: z.string(),
});

export type DataFlowEdge = z.infer<typeof DataFlowEdgeSchema>;

function findPropertyByTitle(
  properties: Property[] | undefined,
  title: string,
): Property | undefined {
  return properties?.find((p) => p.title === title);
}

export function createDataFlowEdge(opts: {
  name: string;
  sourceNode: ComponentWithIO;
  sourceOutput: string;
  destinationNode: ComponentWithIO;
  destinationInput: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): DataFlowEdge {
  const { outputs: sourceOutputs, name: sourceName } = opts.sourceNode;
  const sourceProperty = findPropertyByTitle(sourceOutputs, opts.sourceOutput);
  if (sourceOutputs && sourceOutputs.length > 0 && !sourceProperty) {
    throw new Error(
      `Flow data connection named \`${opts.name}\` is connected to a property ` +
        `named \`${opts.sourceOutput}\` of the source node \`${sourceName}\`, ` +
        `but the node does not have any output property with that name.`,
    );
  }

  const { inputs: destInputs, name: destName } = opts.destinationNode;
  const destProperty = findPropertyByTitle(destInputs, opts.destinationInput);
  if (destInputs && destInputs.length > 0 && !destProperty) {
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
