/**
 * ClientTool - a tool that needs to be run by the client application.
 */
import { z } from "zod";
import type { Property } from "../property.js";
import { ToolBaseSchema } from "./tool.js";

export const ClientToolSchema = ToolBaseSchema.extend({
  componentType: z.literal("ClientTool"),
});

export type ClientTool = z.infer<typeof ClientToolSchema>;

export function createClientTool(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
  requiresConfirmation?: boolean;
}): ClientTool {
  return Object.freeze(
    ClientToolSchema.parse({
      ...opts,
      componentType: "ClientTool" as const,
    }),
  );
}
