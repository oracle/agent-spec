/**
 * ParallelMapNode - same as MapNode but executed in parallel.
 */
import { z } from "zod";
import type { Property, JsonSchemaValue } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";
import { ReductionMethod } from "./map-node.js";

export const ParallelMapNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("ParallelMapNode"),
  subflow: z.lazy(() => z.record(z.unknown())),
  reducers: z
    .record(
      z.enum([
        ReductionMethod.APPEND,
        ReductionMethod.SUM,
        ReductionMethod.AVERAGE,
        ReductionMethod.MAX,
        ReductionMethod.MIN,
      ]),
    )
    .optional(),
});

export type ParallelMapNode = z.infer<typeof ParallelMapNodeSchema>;

function inferMapInputs(subflow: Record<string, unknown>): Property[] {
  const subflowInputs =
    (subflow["inputs"] as Property[] | undefined) ?? [];
  return subflowInputs.map((input) => ({
    jsonSchema: {
      title: `iterated_${input.jsonSchema["title"] as string}`,
      anyOf: [
        input.jsonSchema,
        { type: "array", items: input.jsonSchema },
      ],
    },
    title: `iterated_${input.title}`,
    description: undefined,
    default: undefined,
    type: undefined,
  }));
}

function getDefaultReducers(
  subflow: Record<string, unknown>,
): Record<string, ReductionMethod> {
  const outputs =
    (subflow["outputs"] as Property[] | undefined) ?? [];
  const reducers: Record<string, ReductionMethod> = {};
  for (const output of outputs) {
    const title = output.jsonSchema["title"] as string;
    reducers[title] = ReductionMethod.APPEND;
  }
  return reducers;
}

function inferMapOutputs(
  subflow: Record<string, unknown>,
  reducers: Record<string, ReductionMethod>,
): Property[] {
  const subflowOutputs =
    (subflow["outputs"] as Property[] | undefined) ?? [];
  const outputs: Property[] = [];
  for (const output of subflowOutputs) {
    const title = output.title;
    const reducer = reducers[title];
    if (reducer === undefined) continue;

    let jsonSchema: JsonSchemaValue;
    if (reducer === ReductionMethod.APPEND) {
      jsonSchema = {
        title: `collected_${title}`,
        type: "array",
        items: output.jsonSchema,
      };
    } else {
      jsonSchema = {
        ...output.jsonSchema,
        title: `collected_${title}`,
      };
    }
    outputs.push({
      jsonSchema,
      title: `collected_${title}`,
      description: undefined,
      default: undefined,
      type: jsonSchema["type"] as string | string[] | undefined,
    });
  }
  return outputs;
}

export function createParallelMapNode(opts: {
  name: string;
  subflow: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  reducers?: Record<string, ReductionMethod>;
  inputs?: Property[];
  outputs?: Property[];
}): ParallelMapNode {
  const reducers = opts.reducers ?? getDefaultReducers(opts.subflow);
  const inputs = opts.inputs ?? inferMapInputs(opts.subflow);
  const outputs = opts.outputs ?? inferMapOutputs(opts.subflow, reducers);

  return Object.freeze(
    ParallelMapNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      reducers,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "ParallelMapNode" as const,
    }),
  );
}
