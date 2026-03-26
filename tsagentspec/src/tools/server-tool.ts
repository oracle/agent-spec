/**
 * ServerTool - a tool registered to and executed by the orchestrator.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { ToolBaseSchema } from "./tool.js";

export const ServerToolSchema = ToolBaseSchema.extend({
  componentType: z.literal("ServerTool"),
});

export type ServerTool = z.infer<typeof ServerToolSchema>;

export function createServerTool(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
  requiresConfirmation?: boolean;
}): ServerTool {
  return Object.freeze(
    ServerToolSchema.parse({
      ...opts,
      componentType: "ServerTool" as const,
    }),
  );
}
