import type { JsonSchemaValue, Property } from "../../property.js";
import type { Tool } from "../../tools/index.js";
import {
  MissingMastraToolExecutorError,
  UnsupportedMastraToolError,
} from "./errors.js";
import type {
  MastraToolResolver,
  MastraToolResolverContext,
  MastraToolRuntimeConfig,
} from "./types.js";

export const defaultMastraToolResolver: MastraToolResolver = (
  tool: Tool,
  context: MastraToolResolverContext,
): MastraToolRuntimeConfig => {
  if (tool.componentType !== "ServerTool") {
    throw new UnsupportedMastraToolError(tool.componentType);
  }

  // Match by name first because that is what the LLM sees; id is kept as a
  // useful escape hatch for configs that use stable internal identifiers.
  const executor =
    context.toolRegistry?.[tool.name] ?? context.toolRegistry?.[tool.id];

  if (!executor) {
    throw new MissingMastraToolExecutorError(tool.name);
  }

  return {
    id: tool.name,
    description: tool.description ?? `Agent Spec server tool: ${tool.name}`,
    inputSchema: propertiesToMastraJsonSchema(tool.inputs),
    outputSchema: propertiesToMastraJsonSchema(tool.outputs),
    execute: (input, mastraContext) =>
      executor(input, {
        agentSpecTool: tool,
        agentSpecAgent: context.agent,
        mastraContext,
      }),
    requireApproval: tool.requiresConfirmation,
    sourceAgentSpecTool: tool,
  };
};

export const propertiesToMastraJsonSchema = (
  properties: Property[] | undefined,
): JsonSchemaValue | undefined => {
  if (properties === undefined) {
    return undefined;
  }

  const schemaProperties: Record<string, JsonSchemaValue> = {};
  const required: string[] = [];

  // Agent Spec properties are already JSON Schema fragments. Mastra tools expect
  // one object schema, so we wrap the properties without changing their shape.
  for (const property of properties) {
    schemaProperties[property.title] = property.jsonSchema;
    if (!Object.prototype.hasOwnProperty.call(property.jsonSchema, "default")) {
      required.push(property.title);
    }
  }

  return {
    type: "object",
    properties: schemaProperties,
    required,
    additionalProperties: false,
  };
};
