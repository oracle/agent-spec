/**
 * BuiltinTool - a tool provided by the runtime.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { ToolBaseSchema } from "./tool.js";

export const BuiltinToolSchema = ToolBaseSchema.extend({
  componentType: z.literal("BuiltinTool"),
  toolType: z.string(),
  configuration: z.record(z.unknown()).optional(),
  executorName: z.union([z.string(), z.array(z.string())]).optional(),
  toolVersion: z.string().optional(),
});

export type BuiltinTool = z.infer<typeof BuiltinToolSchema>;

export function createBuiltinTool(opts: {
  name: string;
  toolType: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  configuration?: Record<string, unknown>;
  executorName?: string | string[];
  toolVersion?: string;
  inputs?: Property[];
  outputs?: Property[];
  requiresConfirmation?: boolean;
}): BuiltinTool {
  return Object.freeze(
    BuiltinToolSchema.parse({
      ...opts,
      componentType: "BuiltinTool" as const,
    }),
  );
}
