/**
 * Lazy schema references for breaking circular dependencies in flows.
 *
 * The cycle is: flow.ts -> NodeUnion -> nodes/index.ts -> FlowNodeSchema
 *            -> flow-node.ts -> FlowSchema -> flow.ts.
 *
 * z.lazy() callbacks are only invoked at .parse() time, not at module
 * load time. The registration functions below are called from
 * nodes/index.ts and flow.ts at the module level, which guarantees
 * the backing schemas are populated before any parsing occurs.
 */
import { z } from "zod";

let _nodeUnionSchema: z.ZodType = z.record(z.unknown());
let _flowSchema: z.ZodType = z.record(z.unknown());

/** Lazy reference to NodeUnion — validates at .parse() time. */
export const LazyNodeRef: z.ZodType<Record<string, unknown>> = z.lazy(
  () => _nodeUnionSchema,
);

/** Lazy reference to FlowSchema — validates at .parse() time. */
export const LazyFlowRef: z.ZodType<Record<string, unknown>> = z.lazy(
  () => _flowSchema,
);

/** Called from nodes/index.ts after NodeUnion is defined. */
export function registerNodeUnionSchema(schema: z.ZodType): void {
  _nodeUnionSchema = schema;
}

/** Called from flow.ts after FlowSchema is defined. */
export function registerFlowSchema(schema: z.ZodType): void {
  _flowSchema = schema;
}
