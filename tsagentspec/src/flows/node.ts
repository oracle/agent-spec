/**
 * Node base schema for all flow nodes.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";

/** Default branch name for nodes with a single "next" branch */
export const DEFAULT_NEXT_BRANCH = "next";

/** Base schema for all nodes */
export const NodeBaseSchema = ComponentWithIOSchema.extend({
  branches: z.array(z.string()).default([]),
});

export type NodeBase = z.infer<typeof NodeBaseSchema>;
