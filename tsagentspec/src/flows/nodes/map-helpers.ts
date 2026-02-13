/**
 * Shared helpers for MapNode and ParallelMapNode input/output inference.
 */
import type { Property, JsonSchemaValue } from "../../property.js";
import { ReductionMethod } from "./map-node.js";

/** Infer map inputs by wrapping subflow inputs in iterated_ arrays */
export function inferMapInputs(
  subflow: Record<string, unknown>,
): Property[] {
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

/** Get default reducers (APPEND for each subflow output) */
export function getDefaultReducers(
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

/** Infer map outputs by applying reducers to subflow outputs */
export function inferMapOutputs(
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
