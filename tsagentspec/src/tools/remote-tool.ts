/**
 * RemoteTool - a tool that calls a remote API.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../templating.js";
import { ToolBaseSchema } from "./tool.js";

export const RemoteToolSchema = ToolBaseSchema.extend({
  componentType: z.literal("RemoteTool"),
  url: z.string(),
  httpMethod: z.string(),
  apiSpecUri: z.string().optional(),
  data: z.unknown().default({}),
  queryParams: z.record(z.unknown()).default({}),
  headers: z.record(z.unknown()).default({}),
  sensitiveHeaders: z.record(z.unknown()).default({}),
});

export type RemoteTool = z.infer<typeof RemoteToolSchema>;

function inferRemoteToolInputs(opts: {
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

export function createRemoteTool(opts: {
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
  requiresConfirmation?: boolean;
}): RemoteTool {
  const inputs = opts.inputs ?? inferRemoteToolInputs(opts);
  return Object.freeze(
    RemoteToolSchema.parse({
      ...opts,
      inputs,
      componentType: "RemoteTool" as const,
    }),
  );
}
