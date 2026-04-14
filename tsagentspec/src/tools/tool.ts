/**
 * Base tool schema - all tools extend this.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";

export const ToolBaseSchema = ComponentWithIOSchema.extend({
  requiresConfirmation: z.boolean().default(false),
});

export type ToolBase = z.infer<typeof ToolBaseSchema>;
