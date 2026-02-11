/**
 * InputMessageNode - interrupt flow execution to wait for user input.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../../templating.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const DEFAULT_INPUT_MESSAGE_OUTPUT = "user_input";

export const InputMessageNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("InputMessageNode"),
  message: z.string().optional(),
});

export type InputMessageNode = z.infer<typeof InputMessageNodeSchema>;

export function createInputMessageNode(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  message?: string;
  inputs?: Property[];
  outputs?: Property[];
}): InputMessageNode {
  let inputs: Property[];
  if (opts.inputs !== undefined) {
    inputs = opts.inputs;
  } else if (opts.message !== undefined) {
    inputs = getPlaceholderPropertiesFromJsonObject(opts.message);
  } else {
    inputs = [];
  }

  const outputTitle =
    opts.outputs && opts.outputs.length > 0
      ? opts.outputs[0]!.title
      : DEFAULT_INPUT_MESSAGE_OUTPUT;

  const outputs: Property[] = [
    {
      jsonSchema: {
        title: outputTitle,
        type: "string",
        description: "Input provided by the user",
      },
      title: outputTitle,
      description: "Input provided by the user",
      default: undefined,
      type: "string",
    },
  ];

  return Object.freeze(
    InputMessageNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "InputMessageNode" as const,
    }),
  );
}
