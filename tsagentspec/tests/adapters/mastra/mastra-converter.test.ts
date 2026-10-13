import { describe, expect, it } from "vitest";
import {
  createAgent,
  createClientTool,
  createMCPToolBox,
  createOpenAiConfig,
  createServerTool,
  createStdioTransport,
  stringProperty,
} from "../../../src/index.js";
import {
  convertAgentSpecToMastraAgent,
  DuplicateMastraToolNameError,
  UnsupportedMastraAgentFeatureError,
  UnsupportedMastraToolError,
  type MastraAgentRuntimeConfig,
  type MastraRuntimeAdapter,
  type MastraToolRuntimeConfig,
} from "../../../src/adapters/mastra/index.js";

type FakeTool = {
  kind: "tool";
  config: MastraToolRuntimeConfig;
};

type FakeAgent = {
  kind: "agent";
  config: MastraAgentRuntimeConfig<FakeTool>;
};

const fakeRuntime: MastraRuntimeAdapter<FakeAgent, FakeTool> = {
  createAgent: (config) => ({ kind: "agent", config }),
  createTool: (config) => ({ kind: "tool", config }),
};

describe("Agent Spec to Mastra converter", () => {
  it("converts a basic Agent into a Mastra runtime config", async () => {
    const tool = createServerTool({
      name: "lookup",
      description: "Look up account data",
      inputs: [stringProperty({ title: "accountId" })],
    });
    const agent = createAgent({
      id: "agent-1",
      name: "Support Agent",
      description: "Answers support questions",
      metadata: { team: "support" },
      llmConfig: createOpenAiConfig({
        name: "llm",
        modelId: "gpt-4o-mini",
      }),
      systemPrompt: "You answer support questions.",
      tools: [tool],
    });

    const converted = convertAgentSpecToMastraAgent(agent, {
      runtime: fakeRuntime,
      toolRegistry: {
        lookup: (input) => ({ ok: true, input }),
      },
    });

    expect(converted).toMatchObject({
      kind: "agent",
      config: {
        id: "agent-1",
        name: "Support Agent",
        description: "Answers support questions",
        metadata: { team: "support" },
        instructions: "You answer support questions.",
        model: "openai/gpt-4o-mini",
      },
    });
    expect(Object.keys(converted.config.tools)).toEqual(["lookup"]);
    expect(converted.config.tools.lookup?.config.id).toBe("lookup");
    await expect(
      Promise.resolve(
        converted.config.tools.lookup?.config.execute?.({ accountId: "A-1" }),
      ),
    ).resolves.toEqual({
      ok: true,
      input: { accountId: "A-1" },
    });
  });

  it("fails when two Agent Spec tools map to the same Mastra tool key", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: createOpenAiConfig({
        name: "llm",
        modelId: "gpt-4o-mini",
      }),
      systemPrompt: "Hello",
      tools: [
        createServerTool({ id: "tool-1", name: "lookup" }),
        createServerTool({ id: "tool-2", name: "lookup" }),
      ],
    });

    expect(() =>
      convertAgentSpecToMastraAgent(agent, {
        runtime: fakeRuntime,
        toolRegistry: {
          lookup: () => "ok",
        },
      }),
    ).toThrow(DuplicateMastraToolNameError);
  });

  it("fails explicitly for unsupported tool types", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: createOpenAiConfig({
        name: "llm",
        modelId: "gpt-4o-mini",
      }),
      systemPrompt: "Hello",
      tools: [createClientTool({ name: "client-input" })],
    });

    expect(() =>
      convertAgentSpecToMastraAgent(agent, {
        runtime: fakeRuntime,
      }),
    ).toThrow(UnsupportedMastraToolError);
  });

  it("fails explicitly when toolboxes would be dropped", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: createOpenAiConfig({
        name: "llm",
        modelId: "gpt-4o-mini",
      }),
      systemPrompt: "Hello",
      toolboxes: [
        createMCPToolBox({
          name: "remote-tools",
          clientTransport: createStdioTransport({
            name: "stdio",
            command: "node",
          }),
          toolFilter: [],
        }),
      ],
    });

    expect(() =>
      convertAgentSpecToMastraAgent(agent, {
        runtime: fakeRuntime,
      }),
    ).toThrow(UnsupportedMastraAgentFeatureError);
  });
});
