/**
 * Flow nodes barrel exports and NodeUnion discriminated union.
 */
import { z } from "zod";
import { StartNodeSchema } from "./start-node.js";
import { EndNodeSchema } from "./end-node.js";
import { LlmNodeSchema } from "./llm-node.js";
import { ToolNodeSchema } from "./tool-node.js";
import { AgentNodeSchema } from "./agent-node.js";
import { FlowNodeSchema } from "./flow-node.js";
import { BranchingNodeSchema } from "./branching-node.js";
import { MapNodeSchema } from "./map-node.js";
import { ParallelMapNodeSchema } from "./parallel-map-node.js";
import { ParallelFlowNodeSchema } from "./parallel-flow-node.js";
import { ApiNodeSchema } from "./api-node.js";
import { InputMessageNodeSchema } from "./input-message-node.js";
import { OutputMessageNodeSchema } from "./output-message-node.js";
import { CatchExceptionNodeSchema } from "./catch-exception-node.js";
import { registerNodeUnionSchema } from "../lazy-schemas.js";

/** Discriminated union of all node types */
export const NodeUnion = z.discriminatedUnion("componentType", [
  StartNodeSchema,
  EndNodeSchema,
  LlmNodeSchema,
  ToolNodeSchema,
  AgentNodeSchema,
  FlowNodeSchema,
  BranchingNodeSchema,
  MapNodeSchema,
  ParallelMapNodeSchema,
  ParallelFlowNodeSchema,
  ApiNodeSchema,
  InputMessageNodeSchema,
  OutputMessageNodeSchema,
  CatchExceptionNodeSchema,
]);

registerNodeUnionSchema(NodeUnion);

export type Node = z.infer<typeof NodeUnion>;

export {
  StartNodeSchema,
  createStartNode,
  type StartNode,
} from "./start-node.js";
export {
  EndNodeSchema,
  createEndNode,
  type EndNode,
} from "./end-node.js";
export {
  LlmNodeSchema,
  createLlmNode,
  DEFAULT_LLM_OUTPUT,
  type LlmNode,
} from "./llm-node.js";
export {
  ToolNodeSchema,
  createToolNode,
  type ToolNode,
} from "./tool-node.js";
export {
  AgentNodeSchema,
  createAgentNode,
  type AgentNode,
} from "./agent-node.js";
export {
  FlowNodeSchema,
  createFlowNode,
  type FlowNode,
} from "./flow-node.js";
export {
  BranchingNodeSchema,
  createBranchingNode,
  DEFAULT_BRANCH,
  DEFAULT_INPUT,
  type BranchingNode,
} from "./branching-node.js";
export {
  MapNodeSchema,
  createMapNode,
  ReductionMethod,
  type MapNode,
} from "./map-node.js";
export {
  ParallelMapNodeSchema,
  createParallelMapNode,
  type ParallelMapNode,
} from "./parallel-map-node.js";
export {
  ParallelFlowNodeSchema,
  createParallelFlowNode,
  type ParallelFlowNode,
} from "./parallel-flow-node.js";
export {
  ApiNodeSchema,
  createApiNode,
  DEFAULT_API_OUTPUT,
  type ApiNode,
} from "./api-node.js";
export {
  InputMessageNodeSchema,
  createInputMessageNode,
  DEFAULT_INPUT_MESSAGE_OUTPUT,
  type InputMessageNode,
} from "./input-message-node.js";
export {
  OutputMessageNodeSchema,
  createOutputMessageNode,
  type OutputMessageNode,
} from "./output-message-node.js";
export {
  CatchExceptionNodeSchema,
  createCatchExceptionNode,
  CAUGHT_EXCEPTION_BRANCH,
  DEFAULT_EXCEPTION_INFO_VALUE,
  type CatchExceptionNode,
} from "./catch-exception-node.js";
