/**
 * ToolNode - execute a tool in a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { openComponentUnion, type CustomComponent } from "../../component.js";
import { ToolUnion, type Tool } from "../../tools/index.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const ToolNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("ToolNode"),
  tool: openComponentUnion(ToolUnion),
});

export type ToolNode = z.infer<typeof ToolNodeSchema>;

export function createToolNode(opts: {
  name: string;
  tool: Tool | CustomComponent;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): ToolNode {
  const tool = opts.tool as { inputs?: Property[]; outputs?: Property[] };
  const inputs = opts.inputs ?? tool.inputs ?? [];
  const outputs = opts.outputs ?? tool.outputs ?? [];
  return Object.freeze(
    ToolNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "ToolNode" as const,
    }),
  );
}
