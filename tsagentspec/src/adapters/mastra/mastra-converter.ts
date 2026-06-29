import type { Agent } from "../../agents/index.js";
import {
  DuplicateMastraToolNameError,
  UnsupportedMastraAgentFeatureError,
} from "./errors.js";
import { createDefaultMastraRuntime } from "./runtime.js";
import { defaultMastraModelResolver } from "./model.js";
import type {
  AgentSpecToMastraConversionOptions,
  MastraModelResolver,
  MastraRuntimeAdapter,
  MastraToolRegistry,
  MastraToolResolver,
} from "./types.js";
import { defaultMastraToolResolver } from "./tool.js";

export class AgentSpecToMastraConverter<TAgent = unknown, TTool = unknown> {
  private readonly runtime: MastraRuntimeAdapter<TAgent, TTool>;
  private readonly modelResolver: MastraModelResolver;
  private readonly toolResolver: MastraToolResolver;
  private readonly toolRegistry?: MastraToolRegistry;

  constructor(options: AgentSpecToMastraConversionOptions<TAgent, TTool> = {}) {
    this.runtime =
      options.runtime ??
      createDefaultMastraRuntime<TAgent, TTool>(options.defaultRuntime);
    this.modelResolver = options.modelResolver ?? defaultMastraModelResolver;
    this.toolResolver = options.toolResolver ?? defaultMastraToolResolver;
    this.toolRegistry = options.toolRegistry;
  }

  convert(agent: Agent): TAgent {
    assertSupportedAgent(agent);

    const model = this.modelResolver(agent.llmConfig, { agent });
    const tools: Record<string, TTool> = {};

    // Mastra tools are keyed by name at runtime, so duplicate Agent Spec tool
    // names would silently overwrite each other if we did not stop here.
    for (const tool of agent.tools) {
      if (Object.prototype.hasOwnProperty.call(tools, tool.name)) {
        throw new DuplicateMastraToolNameError(tool.name);
      }

      const toolConfig = this.toolResolver(tool, {
        agent,
        toolRegistry: this.toolRegistry,
      });
      tools[tool.name] = this.runtime.createTool(toolConfig);
    }

    return this.runtime.createAgent({
      id: agent.id,
      name: agent.name,
      ...(agent.description ? { description: agent.description } : {}),
      metadata: agent.metadata,
      instructions: agent.systemPrompt,
      model,
      tools,
      sourceAgentSpecAgent: agent,
    });
  }
}

export const convertAgentSpecToMastraAgent = <TAgent = unknown, TTool = unknown>(
  agent: Agent,
  options: AgentSpecToMastraConversionOptions<TAgent, TTool> = {},
): TAgent => new AgentSpecToMastraConverter(options).convert(agent);

const assertSupportedAgent = (agent: Agent): void => {
  // These features need explicit Mastra mappings rather than being dropped
  // during conversion.
  if (agent.toolboxes.length > 0) {
    throw new UnsupportedMastraAgentFeatureError("Agent.toolboxes");
  }

  if (agent.transforms.length > 0) {
    throw new UnsupportedMastraAgentFeatureError("Agent.transforms");
  }
};
