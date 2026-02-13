/**
 * Weather Agent example — mirrors the Python SDK "weather agent" test pattern.
 *
 * Builds a weather-focused agent with client, server, and remote tools,
 * serializes and deserializes it, and verifies all parts survive the round trip.
 */
import { describe, it, expect } from "vitest";
import {
  createAgent,
  createVllmConfig,
  createClientTool,
  createServerTool,
  createRemoteTool,
  createBuiltinTool,
  stringProperty,
  booleanProperty,
  AgentSpecSerializer,
  AgentSpecDeserializer,
} from "../../src/index.js";

/* ---------- shared helpers ---------- */

function makeLlmConfig() {
  return createVllmConfig({
    name: "agi1",
    url: "http://some.where",
    modelId: "agi_model1",
  });
}

function makeWeatherTools() {
  const cityInput = stringProperty({ title: "city_name", default: "zurich" });
  const forecastOutput = stringProperty({ title: "forecast" });
  const subscriptionOutput = booleanProperty({
    title: "subscription_success",
  });

  const weatherTool = createClientTool({
    name: "get_weather",
    description: "Gets the weather in specified city",
    inputs: [cityInput],
    outputs: [forecastOutput],
  });

  const historyTool = createServerTool({
    name: "get_city_history_info",
    description: "Gets information about the city history",
    inputs: [cityInput],
    outputs: [forecastOutput],
  });

  const newsletterTool = createRemoteTool({
    name: "subscribe_to_city_newsletter",
    description: "Subscribe to the newsletter of a city",
    url: "https://my.url/tool",
    httpMethod: "POST",
    apiSpecUri: "https://my.api.spec.url/tool",
    data: { city_name: "{{city_name}}" },
    queryParams: { my_query_param: "abc" },
    headers: { my_header: "123" },
    outputs: [subscriptionOutput],
  });

  return [weatherTool, historyTool, newsletterTool] as const;
}

/* ---------- tests ---------- */

describe("Weather Agent example", () => {
  it("should create a weather agent with multiple tool types", () => {
    const tools = makeWeatherTools();
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...tools],
    });

    expect(agent.componentType).toBe("Agent");
    expect(agent.tools).toHaveLength(3);
    expect(agent.tools[0]!.componentType).toBe("ClientTool");
    expect(agent.tools[1]!.componentType).toBe("ServerTool");
    expect(agent.tools[2]!.componentType).toBe("RemoteTool");
  });

  it("should infer RemoteTool inputs from data template", () => {
    const [, , newsletterTool] = makeWeatherTools();
    expect(newsletterTool.inputs).toBeDefined();
    const inputTitles = newsletterTool.inputs!.map(
      (i: { title: string }) => i.title,
    );
    expect(inputTitles).toContain("city_name");
  });

  it("should serialize the weather agent to YAML and back", () => {
    const tools = makeWeatherTools();
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...tools],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(agent);
    expect(yaml).toBeDefined();
    expect(yaml.length).toBeGreaterThan(0);

    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Agent");
    expect(restored["name"]).toBe("Funny agent");

    const restoredTools = restored["tools"] as Record<string, unknown>[];
    expect(restoredTools).toHaveLength(3);
    expect(restoredTools[0]!["componentType"]).toBe("ClientTool");
    expect(restoredTools[1]!["componentType"]).toBe("ServerTool");
    expect(restoredTools[2]!["componentType"]).toBe("RemoteTool");
  });

  it("should serialize the weather agent to JSON and back", () => {
    const tools = makeWeatherTools();
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...tools],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const json = serializer.toJson(agent);
    const restored = deserializer.fromJson(json) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Agent");
    expect(restored["name"]).toBe("Funny agent");
  });

  it("should preserve tool inputs/outputs through round trip", () => {
    const tools = makeWeatherTools();
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...tools],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(agent);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;

    const restoredTools = restored["tools"] as Record<string, unknown>[];
    // ClientTool (get_weather) should have city_name input and forecast output
    const clientTool = restoredTools[0]!;
    expect(clientTool["name"]).toBe("get_weather");
    const clientInputs = clientTool["inputs"] as { title: string }[];
    expect(clientInputs.map((i) => i.title)).toContain("city_name");
  });

  it("should work with humanInTheLoop=true (default)", () => {
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...makeWeatherTools()],
      humanInTheLoop: true,
    });
    expect(agent.humanInTheLoop).toBe(true);

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(agent);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["humanInTheLoop"]).toBe(true);
  });

  it("should work with humanInTheLoop=false", () => {
    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...makeWeatherTools()],
      humanInTheLoop: false,
    });
    expect(agent.humanInTheLoop).toBe(false);

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(agent);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["humanInTheLoop"]).toBe(false);
  });

  it("should support agent with builtin tool", () => {
    const tools = makeWeatherTools();
    const builtinTool = createBuiltinTool({
      name: "sample_builtin",
      description: "Builtin sample tool for orchestrator",
      toolType: "orchestrator_builtin",
      configuration: { key: "value" },
      executorName: "demo_executor",
      toolVersion: "1.0",
    });

    const agent = createAgent({
      name: "Funny agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "No matter what the user asks, don't reply but make a joke instead",
      tools: [...tools, builtinTool],
    });

    expect(agent.tools).toHaveLength(4);
    expect(agent.tools[3]!.componentType).toBe("BuiltinTool");

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const yaml = serializer.toYaml(agent);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    const restoredTools = restored["tools"] as Record<string, unknown>[];
    expect(restoredTools).toHaveLength(4);
    expect(restoredTools[3]!["componentType"]).toBe("BuiltinTool");
    expect(restoredTools[3]!["toolType"]).toBe("orchestrator_builtin");
  });
});
