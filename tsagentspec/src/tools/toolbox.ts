/**
 * ToolBox and MCPToolBox.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { ClientTransportUnion, type ClientTransport } from "../mcp/client-transport.js";
import { MCPToolSpecSchema } from "../mcp/mcp-tool.js";

export const MCPToolBoxSchema = ComponentBaseSchema.extend({
  componentType: z.literal("MCPToolBox"),
  clientTransport: ClientTransportUnion,
  toolFilter: z
    .array(z.union([MCPToolSpecSchema, z.string()]))
    .optional(),
});

export type MCPToolBox = z.infer<typeof MCPToolBoxSchema>;

export function createMCPToolBox(opts: {
  name: string;
  clientTransport: ClientTransport;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  toolFilter?: Array<z.infer<typeof MCPToolSpecSchema> | string>;
}): MCPToolBox {
  return Object.freeze(
    MCPToolBoxSchema.parse({
      ...opts,
      componentType: "MCPToolBox" as const,
    }),
  );
}

export const ToolBoxUnion = z.discriminatedUnion("componentType", [
  MCPToolBoxSchema,
]);

export type ToolBox = z.infer<typeof ToolBoxUnion>;
