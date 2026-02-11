/**
 * ApiNode - make an API call as part of a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../../templating.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const DEFAULT_API_OUTPUT = "response";

export const ApiNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("ApiNode"),
  url: z.string(),
  httpMethod: z.string(),
  apiSpecUri: z.string().optional(),
  data: z.unknown().default({}),
  queryParams: z.record(z.unknown()).default({}),
  headers: z.record(z.unknown()).default({}),
  sensitiveHeaders: z.record(z.unknown()).default({}),
});

export type ApiNode = z.infer<typeof ApiNodeSchema>;

function inferApiNodeInputs(opts: {
  url: string;
  httpMethod: string;
  apiSpecUri?: string;
  data?: unknown;
  queryParams?: Record<string, unknown>;
  headers?: Record<string, unknown>;
}): Property[] {
  return getPlaceholderPropertiesFromJsonObject([
    opts.url,
    opts.httpMethod,
    opts.apiSpecUri ?? "",
    opts.data ?? {},
    opts.queryParams ?? {},
    opts.headers ?? {},
  ]);
}

export function createApiNode(opts: {
  name: string;
  url: string;
  httpMethod: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  apiSpecUri?: string;
  data?: unknown;
  queryParams?: Record<string, unknown>;
  headers?: Record<string, unknown>;
  sensitiveHeaders?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): ApiNode {
  const inputs = opts.inputs ?? inferApiNodeInputs(opts);
  const outputs = opts.outputs ?? [
    {
      jsonSchema: { title: DEFAULT_API_OUTPUT },
      title: DEFAULT_API_OUTPUT,
      description: undefined,
      default: undefined,
      type: undefined,
    },
  ];

  return Object.freeze(
    ApiNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "ApiNode" as const,
    }),
  );
}
