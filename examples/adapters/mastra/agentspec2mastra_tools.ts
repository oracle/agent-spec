/**
 * Agent Spec -> Mastra example.
 *
 * Creates an Agent Spec agent, serializes it to YAML, and loads that YAML into
 * a Mastra-shaped runtime using the TypeScript Mastra adapter.
 */
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  numberProperty,
} from "../../../tsagentspec/src/index.js";
import {
  AgentSpecLoader,
  type MastraAgentRuntimeConfig,
  type MastraRuntimeAdapter,
  type MastraToolRuntimeConfig,
} from "../../../tsagentspec/src/adapters/mastra/index.js";

type ExampleMastraTool = {
  id: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  execute: (input: unknown) => unknown | Promise<unknown>;
};

type ExampleMastraAgent = {
  id: string;
  name: string;
  instructions: string;
  model: unknown;
  tools: Record<string, ExampleMastraTool>;
};

const subtractionTool = createServerTool({
  name: "subtraction-tool",
  description: "Subtract two numbers.",
  inputs: [numberProperty({ title: "a" }), numberProperty({ title: "b" })],
  outputs: [numberProperty({ title: "difference" })],
});

const llmConfig = createOpenAiCompatibleConfig({
  name: "example-model",
  modelId: "oci/openai.gpt-5.4-mini",
  url: "https://example-llm-endpoint.invalid/v1",
});

const agent = createAgent({
  name: "agentspec_mastra_subtraction_agent",
  description: "Agent Spec agent loaded into a Mastra-shaped runtime.",
  llmConfig,
  systemPrompt: "Use the subtraction tool when the user asks for subtraction.",
  tools: [subtractionTool],
});

const yaml = new AgentSpecSerializer().toYaml(agent) as string;

const exampleRuntime: MastraRuntimeAdapter<
  ExampleMastraAgent,
  ExampleMastraTool
> = {
  createAgent(config: MastraAgentRuntimeConfig<ExampleMastraTool>) {
    return {
      id: config.id,
      name: config.name,
      instructions: config.instructions,
      model: config.model,
      tools: config.tools,
    };
  },

  createTool(config: MastraToolRuntimeConfig) {
    const execute = config.execute;
    if (execute === undefined) {
      throw new Error(`Missing executor for tool '${config.id}'.`);
    }

    return {
      id: config.id,
      description: config.description,
      inputSchema: config.inputSchema,
      outputSchema: config.outputSchema,
      execute,
    };
  },
};

const loader = new AgentSpecLoader({
  runtime: exampleRuntime,
  toolRegistry: {
    "subtraction-tool": (input) => {
      const args = input as { a: number; b: number };
      return { difference: args.a - args.b };
    },
  },
});

const main = async (): Promise<void> => {
  const mastraAgent = loader.loadYaml(yaml);
  const subtraction = mastraAgent.tools["subtraction-tool"];
  if (subtraction === undefined) {
    throw new Error("Expected subtraction tool to be loaded.");
  }

  const result = await subtraction.execute({ a: 987654321, b: 123456789 });

  console.log("Agent Spec YAML:");
  console.log(yaml);
  console.log("Loaded Mastra-shaped agent:", mastraAgent.name);
  console.log("Tool result:", result);
};

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
