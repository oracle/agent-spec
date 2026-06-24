import { AgentSchema, createAgent, type Agent } from "../../agents/index.js";
import { FlowSchema, type Flow } from "../../flows/index.js";
import {
  createOllamaConfig,
  createOpenAiCompatibleConfig,
  createOpenAiConfig,
  createVllmConfig,
  LlmConfigUnion,
  type LlmConfig,
} from "../../llms/index.js";
import {
  propertyFromJsonSchema,
  type JsonSchemaValue,
  type Property,
} from "../../property.js";
import {
  createBuiltinTool,
  createServerTool,
  ToolUnion,
  type Tool,
} from "../../tools/index.js";
import { UnsupportedMastraExportError } from "./errors.js";

export type AgentSpecExportedComponent = Agent | Flow;

export type MastraModelExportContext = {
  agentName?: string;
};

export type MastraToolExportContext = {
  toolName: string;
  tool: unknown;
};

export type MastraToAgentSpecConversionOptions = {
  nativeModelExporter?: (
    model: unknown,
    context: MastraModelExportContext,
  ) => LlmConfig;
  nativeToolExporter?: (
    tool: unknown,
    context: MastraToolExportContext,
  ) => Tool | undefined;
  defaultModelName?: string;
  nativeModelBaseUrls?: Record<string, string | undefined>;
  includeModelApiKey?: boolean;
};

export class MastraToAgentSpecConverter {
  private readonly options: MastraToAgentSpecConversionOptions;

  constructor(options: MastraToAgentSpecConversionOptions = {}) {
    this.options = options;
  }

  convert(input: unknown): AgentSpecExportedComponent {
    const agent = this.tryExportAgent(input);
    if (agent) {
      return agent;
    }

    const flow = this.tryExportFlow(input);
    if (flow) {
      return flow;
    }

    throw new UnsupportedMastraExportError(
      "Cannot export Mastra object to Agent Spec. Provide an adapter-created object with Agent Spec provenance, or a simple serializable native agent config.",
    );
  }

  toAgent(input: unknown): Agent {
    const agent = this.tryExportAgent(input);
    if (!agent) {
      throw new UnsupportedMastraExportError(
        "Cannot export Mastra agent to Agent Spec. Runtime-only agents without Agent Spec provenance or serializable native config are unsupported.",
      );
    }
    return agent;
  }

  toFlow(input: unknown): Flow {
    const flow = this.tryExportFlow(input);
    if (!flow) {
      throw new UnsupportedMastraExportError(
        "Cannot export Mastra workflow to Agent Spec. Workflow export currently requires adapter-created Agent Spec flow provenance.",
      );
    }
    return flow;
  }

  private tryExportAgent(input: unknown): Agent | undefined {
    // Provenance is the lossless path: objects produced by this adapter keep the
    // original Agent Spec component attached to their runtime config.
    const sourceAgent = findAgentSpecAgent(input);
    if (sourceAgent) {
      return sourceAgent;
    }

    // Native Mastra export is intentionally narrower. We only accept plain,
    // serializable config objects that can be represented in Agent Spec.
    const nativeConfig = resolveNativeAgentConfig(input);
    if (!nativeConfig) {
      return undefined;
    }

    return this.exportNativeAgent(nativeConfig);
  }

  private tryExportFlow(input: unknown): Flow | undefined {
    return findAgentSpecFlow(input);
  }

  private exportNativeAgent(config: Record<string, unknown>): Agent {
    const name = requiredString(config["name"], "native Mastra agent name");
    const instructions = requiredString(
      config["instructions"] ?? config["systemPrompt"],
      `native Mastra agent '${name}' instructions`,
    );
    const metadata = optionalRecord(
      config["metadata"],
      `native Mastra agent '${name}' metadata`,
    );
    const model = this.exportNativeModel(config["model"] ?? config["llmConfig"], {
      agentName: name,
    });
    const tools = this.exportNativeTools(config["tools"]);

    return createAgent({
      name,
      id: optionalString(config["id"]),
      description: optionalString(config["description"]),
      metadata,
      llmConfig: model,
      systemPrompt: instructions,
      tools,
    });
  }

  private exportNativeModel(
    model: unknown,
    context: MastraModelExportContext,
  ): LlmConfig {
    if (this.options.nativeModelExporter) {
      return this.options.nativeModelExporter(model, context);
    }

    // If the caller already gave us an Agent Spec LLM config, keep it as-is.
    const parsed = LlmConfigUnion.safeParse(model);
    if (parsed.success) {
      return parsed.data;
    }

    if (typeof model === "function") {
      throw new UnsupportedMastraExportError(
        "Cannot export dynamic Mastra model resolver functions to Agent Spec.",
      );
    }

    if (Array.isArray(model)) {
      throw new UnsupportedMastraExportError(
        "Cannot export Mastra model fallback arrays to a single Agent Spec LLM config.",
      );
    }

    if (typeof model === "string") {
      return this.exportModelId(model, {});
    }

    if (isRecord(model)) {
      const provider = optionalString(model["provider"]);
      const modelId =
        optionalString(model["id"]) ??
        optionalString(model["modelId"]) ??
        optionalString(model["model"]) ??
        optionalString(model["name"]);
      const url =
        optionalString(model["url"]) ??
        optionalString(model["baseUrl"]) ??
        optionalString(model["baseURL"]);
      const apiKey = this.options.includeModelApiKey
        ? optionalString(model["apiKey"])
        : undefined;

      if (!modelId) {
        throw new UnsupportedMastraExportError(
          "Cannot export native Mastra model object without a string id/model/name.",
        );
      }

      return this.exportModelId(modelId, { provider, url, apiKey });
    }

    throw new UnsupportedMastraExportError(
      "Cannot export native Mastra model. Use Agent Spec provenance or provide nativeModelExporter.",
    );
  }

  private exportModelId(
    modelId: string,
    options: {
      provider?: string;
      url?: string;
      apiKey?: string;
    },
  ): LlmConfig {
    const parsed = parseProviderModelId(modelId, options.provider);
    const provider = parsed.provider;
    const id = parsed.modelId;
    const name = this.options.defaultModelName ?? "mastra-native-model";
    const url =
      options.url ??
      this.options.nativeModelBaseUrls?.[provider] ??
      this.options.nativeModelBaseUrls?.["openai-compatible"];

    if (provider === "openai") {
      return createOpenAiConfig({
        name,
        modelId: id,
        apiKey: options.apiKey,
      });
    }

    if (provider === "ollama" && url) {
      return createOllamaConfig({
        name,
        modelId: id,
        url,
        apiKey: options.apiKey,
      });
    }

    if (provider === "vllm" && url) {
      return createVllmConfig({
        name,
        modelId: id,
        url,
        apiKey: options.apiKey,
      });
    }

    if (url) {
      return createOpenAiCompatibleConfig({
        name,
        modelId: id,
        url,
        apiKey: options.apiKey,
      });
    }

    throw new UnsupportedMastraExportError(
      `Cannot export native Mastra model '${modelId}'. Only OpenAI model ids are portable without a base URL.`,
    );
  }

  private exportNativeTools(toolsInput: unknown): Tool[] {
    if (toolsInput === undefined || toolsInput === null) {
      return [];
    }

    if (Array.isArray(toolsInput)) {
      return toolsInput.map((tool, index) =>
        this.exportNativeTool(tool, `tool_${index + 1}`),
      );
    }

    if (!isRecord(toolsInput)) {
      throw new UnsupportedMastraExportError(
        "Cannot export native Mastra tools unless tools are provided as an array or object map.",
      );
    }

    return Object.entries(toolsInput).map(([toolName, tool]) =>
      this.exportNativeTool(tool, toolName),
    );
  }

  private exportNativeTool(tool: unknown, fallbackName: string): Tool {
    // Runtime-created tools from the loader carry their source Agent Spec tool,
    // which is safer than reconstructing the contract from runtime fields.
    const sourceTool = findAgentSpecTool(tool);
    if (sourceTool) {
      return sourceTool;
    }

    const custom = this.options.nativeToolExporter?.(tool, {
      toolName: fallbackName,
      tool,
    });
    if (custom) {
      return custom;
    }

    const parsed = ToolUnion.safeParse(tool);
    if (parsed.success) {
      return parsed.data;
    }

    if (!isRecord(tool)) {
      throw new UnsupportedMastraExportError(
        `Cannot export native Mastra tool '${fallbackName}' without a serializable tool descriptor.`,
      );
    }

    const toolConfig = isRecord(tool["config"])
      ? (tool["config"] as Record<string, unknown>)
      : tool;
    const name =
      optionalString(toolConfig["name"]) ??
      optionalString(toolConfig["id"]) ??
      fallbackName;
    const description = optionalString(toolConfig["description"]);
    const metadata = optionalRecord(
      toolConfig["metadata"],
      `native Mastra tool '${name}' metadata`,
    );
    const requiresConfirmation = optionalBoolean(
      toolConfig["requiresConfirmation"] ?? toolConfig["requireApproval"],
      `native Mastra tool '${name}' requireApproval`,
    );
    const inputs = jsonSchemaToProperties(toolConfig["inputSchema"], name);
    const outputs = jsonSchemaToProperties(toolConfig["outputSchema"], name);
    const toolType = optionalString(toolConfig["toolType"]);

    // A plain `toolType` describes a runtime-provided tool. Without it, the
    // portable representation is a ServerTool backed by a runtime registry.
    if (toolType) {
      return createBuiltinTool({
        name,
        id: optionalString(toolConfig["id"]),
        description,
        metadata,
        toolType,
        configuration: optionalRecord(
          toolConfig["configuration"],
          `native Mastra tool '${name}' configuration`,
        ),
        executorName: optionalExecutorName(toolConfig["executorName"]),
        toolVersion: optionalString(toolConfig["toolVersion"]),
        inputs,
        outputs,
        requiresConfirmation,
      });
    }

    return createServerTool({
      name,
      id: optionalString(toolConfig["id"]),
      description,
      metadata,
      inputs,
      outputs,
      requiresConfirmation,
    });
  }
}

const findAgentSpecAgent = (input: unknown): Agent | undefined => {
  const direct = parseAgent(input);
  if (direct) {
    return direct;
  }

  return findByComponentType(input, "Agent", parseAgent);
};

const findAgentSpecFlow = (input: unknown): Flow | undefined => {
  const direct = parseFlow(input);
  if (direct) {
    return direct;
  }

  return findByComponentType(input, "Flow", parseFlow);
};

const findAgentSpecTool = (input: unknown): Tool | undefined => {
  const parsed = ToolUnion.safeParse(input);
  if (parsed.success) {
    return parsed.data;
  }

  return findByComponentType(input, undefined, (value) => {
    const result = ToolUnion.safeParse(value);
    return result.success ? result.data : undefined;
  });
};

const parseAgent = (input: unknown): Agent | undefined => {
  const parsed = AgentSchema.safeParse(input);
  return parsed.success ? parsed.data : undefined;
};

const parseFlow = (input: unknown): Flow | undefined => {
  const parsed = FlowSchema.safeParse(input);
  return parsed.success ? parsed.data : undefined;
};

const findByComponentType = <T>(
  input: unknown,
  componentType: string | undefined,
  parse: (value: unknown) => T | undefined,
): T | undefined => {
  // Adapter-created objects usually tuck provenance under config/source fields.
  // Keep the search shallow so arbitrary runtime objects are not walked forever.
  const visited = new Set<unknown>();
  const queue: Array<{ value: unknown; depth: number }> = [
    { value: input, depth: 0 },
  ];

  while (queue.length > 0) {
    const { value, depth } = queue.shift()!;
    if (!isRecord(value) || visited.has(value)) {
      continue;
    }
    visited.add(value);

    if (
      (componentType === undefined || value["componentType"] === componentType) &&
      depth > 0
    ) {
      const parsed = parse(value);
      if (parsed) {
        return parsed;
      }
    }

    if (depth >= 3) {
      continue;
    }

    for (const key of [
      "sourceAgentSpecAgent",
      "sourceAgentSpecFlow",
      "sourceAgentSpecTool",
      "config",
      "source",
      "rawConfig",
    ]) {
      const next = value[key];
      if (next !== undefined) {
        queue.push({ value: next, depth: depth + 1 });
      }
    }
  }

  return undefined;
};

const resolveNativeAgentConfig = (
  input: unknown,
): Record<string, unknown> | undefined => {
  if (!isRecord(input)) {
    return undefined;
  }

  if (isNativeAgentConfig(input)) {
    return input;
  }

  const config = input["config"];
  if (isRecord(config) && isNativeAgentConfig(config)) {
    return config;
  }

  return undefined;
};

const isNativeAgentConfig = (value: Record<string, unknown>): boolean =>
  typeof value["name"] === "string" &&
  (value["instructions"] !== undefined || value["systemPrompt"] !== undefined) &&
  (value["model"] !== undefined || value["llmConfig"] !== undefined);

const parseProviderModelId = (
  modelId: string,
  explicitProvider?: string,
): { provider: string; modelId: string } => {
  if (explicitProvider) {
    return { provider: explicitProvider.toLowerCase(), modelId };
  }

  const separator = modelId.indexOf("/");
  if (separator <= 0 || separator === modelId.length - 1) {
    return { provider: "openai", modelId };
  }

  return {
    provider: modelId.slice(0, separator).toLowerCase(),
    modelId: modelId.slice(separator + 1),
  };
};

const jsonSchemaToProperties = (
  schemaInput: unknown,
  fallbackTitle: string,
): Property[] | undefined => {
  const schema = extractJsonSchema(schemaInput);
  if (!schema) {
    return undefined;
  }

  if (schema["type"] === "object" && isRecord(schema["properties"])) {
    return Object.entries(schema["properties"]).map(([name, propertySchema]) => {
      if (!isRecord(propertySchema)) {
        throw new UnsupportedMastraExportError(
          `Cannot export JSON schema property '${name}' because it is not an object schema.`,
        );
      }
      return propertyFromJsonSchema({
        title: name,
        ...propertySchema,
      });
    });
  }

  return [
    propertyFromJsonSchema({
      title: fallbackTitle,
      ...schema,
    }),
  ];
};

const extractJsonSchema = (schemaInput: unknown): JsonSchemaValue | undefined => {
  if (schemaInput === undefined || schemaInput === null) {
    return undefined;
  }

  if (isRecord(schemaInput) && isRecord(schemaInput["jsonSchema"])) {
    return schemaInput["jsonSchema"] as JsonSchemaValue;
  }

  if (isRecord(schemaInput) && isRecord(schemaInput["_def"])) {
    throw new UnsupportedMastraExportError(
      "Cannot export Zod runtime schemas from native Mastra tools. Provide JSON Schema or nativeToolExporter.",
    );
  }

  if (isRecord(schemaInput)) {
    return schemaInput as JsonSchemaValue;
  }

  throw new UnsupportedMastraExportError(
    "Cannot export native Mastra tool schema unless it is JSON Schema.",
  );
};

const requiredString = (value: unknown, label: string): string => {
  if (typeof value === "function") {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label} because it is a runtime function.`,
    );
  }
  if (typeof value !== "string" || value.length === 0) {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label}; expected a non-empty string.`,
    );
  }
  return value;
};

const optionalString = (value: unknown): string | undefined =>
  typeof value === "string" && value.length > 0 ? value : undefined;

const optionalBoolean = (
  value: unknown,
  label: string,
): boolean | undefined => {
  if (value === undefined) {
    return undefined;
  }
  if (typeof value === "function") {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label} because it is a runtime function.`,
    );
  }
  if (typeof value !== "boolean") {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label}; expected a boolean.`,
    );
  }
  return value;
};

const optionalRecord = (
  value: unknown,
  label: string,
): Record<string, unknown> | undefined => {
  if (value === undefined) {
    return undefined;
  }
  if (typeof value === "function") {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label} because it is a runtime function.`,
    );
  }
  if (!isRecord(value)) {
    throw new UnsupportedMastraExportError(
      `Cannot export ${label}; expected an object.`,
    );
  }
  return value;
};

const optionalExecutorName = (value: unknown): string | string[] | undefined => {
  if (value === undefined) {
    return undefined;
  }
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return value;
  }
  throw new UnsupportedMastraExportError(
    "Cannot export native Mastra built-in tool executorName; expected string or string array.",
  );
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
