/**
 * Base component schemas and types.
 *
 * All components extend ComponentBaseSchema.
 * Components with inputs/outputs extend ComponentWithIOSchema.
 */
import { z } from "zod";
import { PropertySchema } from "./property.js";

/** Base component schema - all components extend this */
export const ComponentBaseSchema = z.object({
  id: z.string().min(1).default(() => crypto.randomUUID()),
  name: z.string(),
  description: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
  componentType: z.string(),
});

export type ComponentBase = z.infer<typeof ComponentBaseSchema>;

/** ComponentWithIO adds inputs/outputs */
export const ComponentWithIOSchema = ComponentBaseSchema.extend({
  inputs: z.array(PropertySchema).optional(),
  outputs: z.array(PropertySchema).optional(),
});

export type ComponentWithIO = z.infer<typeof ComponentWithIOSchema>;

/** Check if a value is a component (has string id, name, componentType) */
export function isComponent(value: unknown): value is ComponentBase {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj["id"] === "string" &&
    typeof obj["name"] === "string" &&
    typeof obj["componentType"] === "string"
  );
}

/** Abstract type markers for discriminated unions */
export type AbstractComponentType =
  | "Component"
  | "ComponentWithIO"
  | "AgenticComponent"
  | "Node"
  | "Tool"
  | "LlmConfig"
  | "ToolBox"
  | "OciClientConfig"
  | "ClientTransport"
  | "Datastore"
  | "MessageTransform";

/** All concrete builtin component type names (the keys of the component registry) */
export const BUILTIN_COMPONENT_TYPE_NAMES = [
  "Agent",
  "Swarm",
  "ManagerWorkers",
  "RemoteAgent",
  "A2AAgent",
  "SpecializedAgent",
  "Flow",
  "StartNode",
  "EndNode",
  "LlmNode",
  "ToolNode",
  "AgentNode",
  "FlowNode",
  "BranchingNode",
  "MapNode",
  "ParallelMapNode",
  "ParallelFlowNode",
  "ApiNode",
  "InputMessageNode",
  "OutputMessageNode",
  "CatchExceptionNode",
  "ServerTool",
  "ClientTool",
  "RemoteTool",
  "BuiltinTool",
  "MCPTool",
  "MCPToolSpec",
  "OpenAiCompatibleConfig",
  "OllamaConfig",
  "VllmConfig",
  "OpenAiConfig",
  "OciGenAiConfig",
  "ControlFlowEdge",
  "DataFlowEdge",
  "MCPToolBox",
  "StdioTransport",
  "SSETransport",
  "SSEmTLSTransport",
  "StreamableHTTPTransport",
  "StreamableHTTPmTLSTransport",
  "RemoteTransport",
  "OciClientConfigWithApiKey",
  "OciClientConfigWithInstancePrincipal",
  "OciClientConfigWithResourcePrincipal",
  "OciClientConfigWithSecurityToken",
  "InMemoryCollectionDatastore",
  "OracleDatabaseDatastore",
  "PostgresDatabaseDatastore",
  "TlsOracleDatabaseConnectionConfig",
  "MTlsOracleDatabaseConnectionConfig",
  "TlsPostgresDatabaseConnectionConfig",
  "A2AConnectionConfig",
  "AgentSpecializationParameters",
  "MessageSummarizationTransform",
  "ConversationSummarizationTransform",
] as const;

/** All concrete component type string literals */
export type ComponentTypeName = (typeof BUILTIN_COMPONENT_TYPE_NAMES)[number];

const BUILTIN_COMPONENT_TYPE_NAME_SET: ReadonlySet<string> = new Set(
  BUILTIN_COMPONENT_TYPE_NAMES,
);

/** Check if a component type name is one of the builtin component types */
export function isBuiltinComponentTypeName(
  componentType: string,
): componentType is ComponentTypeName {
  return BUILTIN_COMPONENT_TYPE_NAME_SET.has(componentType);
}

/**
 * A component whose type is provided by serialization/deserialization plugins rather than
 * being one of the builtin component types.
 *
 * Only the base component fields are validated; the plugin-specific fields are kept as-is.
 */
export const CustomComponentSchema = ComponentBaseSchema.passthrough().refine(
  (component) => !isBuiltinComponentTypeName(component.componentType),
  {
    message: "Builtin component types are validated by their own schema",
    path: ["componentType"],
  },
);

export type CustomComponent = ComponentBase & { [key: string]: unknown };

/** Check if a value is a component-like object with a non-builtin componentType */
function hasCustomComponentType(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const componentType = (value as Record<string, unknown>)["componentType"];
  return (
    typeof componentType === "string" && !isBuiltinComponentTypeName(componentType)
  );
}

/**
 * Open a union of builtin component schemas to plugin-provided (custom) components.
 *
 * Builtin component types are still validated by `builtinUnion`, so a builtin component of
 * the wrong kind (e.g. an Agent where a Tool is expected) is rejected as before. Components
 * with a non-builtin `componentType` are validated with `CustomComponentSchema` instead.
 * This mirrors pyagentspec, where a field typed with an abstract component accepts
 * user-defined subclasses, and lets custom components nested inside builtin components
 * round-trip through the plugin system.
 */
export function openComponentUnion<Schema extends z.ZodTypeAny>(
  builtinUnion: Schema,
): z.ZodType<
  z.output<Schema> | CustomComponent,
  z.ZodTypeDef,
  z.input<Schema> | CustomComponent
> {
  const schema = z.unknown().transform((value, ctx) => {
    const target: z.ZodTypeAny = hasCustomComponentType(value)
      ? CustomComponentSchema
      : builtinUnion;
    const result = target.safeParse(value);
    if (!result.success) {
      for (const issue of result.error.issues) {
        ctx.addIssue(issue);
      }
      return z.NEVER;
    }
    return result.data as z.output<Schema> | CustomComponent;
  });
  return schema as unknown as z.ZodType<
    z.output<Schema> | CustomComponent,
    z.ZodTypeDef,
    z.input<Schema> | CustomComponent
  >;
}
