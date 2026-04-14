/**
 * Tools barrel export.
 */
import { z } from "zod";
import { ServerToolSchema } from "./server-tool.js";
import { ClientToolSchema } from "./client-tool.js";
import { RemoteToolSchema } from "./remote-tool.js";
import { BuiltinToolSchema } from "./builtin-tool.js";
import { MCPToolSchema } from "../mcp/mcp-tool.js";

/** Discriminated union of all tool types */
export const ToolUnion = z.discriminatedUnion("componentType", [
  ServerToolSchema,
  ClientToolSchema,
  RemoteToolSchema,
  BuiltinToolSchema,
  MCPToolSchema,
]);

export type Tool = z.infer<typeof ToolUnion>;

export { ToolBaseSchema, type ToolBase } from "./tool.js";
export {
  ServerToolSchema,
  createServerTool,
  type ServerTool,
} from "./server-tool.js";
export {
  ClientToolSchema,
  createClientTool,
  type ClientTool,
} from "./client-tool.js";
export {
  RemoteToolSchema,
  createRemoteTool,
  type RemoteTool,
} from "./remote-tool.js";
export {
  BuiltinToolSchema,
  createBuiltinTool,
  type BuiltinTool,
} from "./builtin-tool.js";
export {
  ToolBoxUnion,
  MCPToolBoxSchema,
  createMCPToolBox,
  type ToolBox,
  type MCPToolBox,
} from "./toolbox.js";
