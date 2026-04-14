/**
 * Adaptive Expert example — mirrors the Python SDK multi-agent patterns.
 *
 * Tests Swarm, ManagerWorkers, and SpecializedAgent configurations including
 * serialization round trips.
 */
import { describe, it, expect } from "vitest";
import {
  createAgent,
  createVllmConfig,
  createSwarm,
  createManagerWorkers,
  createSpecializedAgent,
  createAgentSpecializationParameters,
  createServerTool,
  stringProperty,
  HandoffMode,
  AgentSpecSerializer,
  AgentSpecDeserializer,
} from "../../src/index.js";

/* ---------- shared helpers ---------- */

function makeLlmConfig() {
  return createVllmConfig({
    name: "model",
    url: "http://some.where",
    modelId: "expert_model",
  });
}

function makeExpertAgent(name: string, expertise: string) {
  return createAgent({
    name,
    llmConfig: makeLlmConfig(),
    systemPrompt: `You are an expert in ${expertise}. Always stay on topic.`,
  });
}

/* ---------- Swarm tests ---------- */

describe("Adaptive Expert: Swarm pattern", () => {
  it("should create a swarm of expert agents", () => {
    const mathAgent = makeExpertAgent("math-expert", "mathematics");
    const codeAgent = makeExpertAgent("code-expert", "software engineering");
    const scienceAgent = makeExpertAgent("science-expert", "natural science");

    const swarm = createSwarm({
      name: "expert-swarm",
      firstAgent: mathAgent,
      relationships: [
        [mathAgent, codeAgent],
        [codeAgent, scienceAgent],
        [scienceAgent, mathAgent],
      ],
      handoff: HandoffMode.OPTIONAL,
    });

    expect(swarm.componentType).toBe("Swarm");
    expect(swarm.name).toBe("expert-swarm");
    expect(swarm.relationships).toHaveLength(3);
    expect(swarm.handoff).toBe("optional");
  });

  it("should serialize and deserialize a swarm", () => {
    const agentA = makeExpertAgent("agent-a", "topic A");
    const agentB = makeExpertAgent("agent-b", "topic B");

    const swarm = createSwarm({
      name: "two-agent-swarm",
      firstAgent: agentA,
      relationships: [[agentA, agentB]],
      handoff: HandoffMode.ALWAYS,
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(swarm);
    expect(yaml).toContain("Swarm");
    expect(yaml.length).toBeGreaterThan(0);

    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Swarm");
    expect(restored["name"]).toBe("two-agent-swarm");
    expect(restored["handoff"]).toBe("always");
    expect(
      (restored["relationships"] as unknown[][]).length,
    ).toBe(1);
  });

  it("should support all handoff modes", () => {
    const a = makeExpertAgent("a", "x");
    const b = makeExpertAgent("b", "y");

    for (const mode of [
      HandoffMode.NEVER,
      HandoffMode.OPTIONAL,
      HandoffMode.ALWAYS,
    ]) {
      const swarm = createSwarm({
        name: `swarm-${mode}`,
        firstAgent: a,
        relationships: [[a, b]],
        handoff: mode,
      });
      expect(swarm.handoff).toBe(mode);
    }
  });

  it("should default handoff to optional", () => {
    const a = makeExpertAgent("a", "x");
    const b = makeExpertAgent("b", "y");
    const swarm = createSwarm({
      name: "swarm",
      firstAgent: a,
      relationships: [[a, b]],
    });
    expect(swarm.handoff).toBe("optional");
  });
});

/* ---------- ManagerWorkers tests ---------- */

describe("Adaptive Expert: ManagerWorkers pattern", () => {
  it("should create a manager-workers setup", () => {
    const manager = makeExpertAgent("manager", "coordination");
    const worker1 = makeExpertAgent("worker-1", "data analysis");
    const worker2 = makeExpertAgent("worker-2", "report writing");

    const mw = createManagerWorkers({
      name: "analysis-team",
      groupManager: manager,
      workers: [worker1, worker2],
    });

    expect(mw.componentType).toBe("ManagerWorkers");
    expect(mw.name).toBe("analysis-team");
    expect(mw.workers).toHaveLength(2);
  });

  it("should serialize and deserialize ManagerWorkers", () => {
    const manager = makeExpertAgent("manager", "coordination");
    const worker = makeExpertAgent("worker", "execution");

    const mw = createManagerWorkers({
      name: "team",
      groupManager: manager,
      workers: [worker],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(mw);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("ManagerWorkers");
    expect(restored["name"]).toBe("team");
    expect(
      (restored["workers"] as unknown[]).length,
    ).toBe(1);
  });

  it("should nest ManagerWorkers in a Swarm", () => {
    const manager = makeExpertAgent("manager", "coordination");
    const worker = makeExpertAgent("worker", "analysis");
    const mw = createManagerWorkers({
      name: "team",
      groupManager: manager,
      workers: [worker],
    });

    const standaloneAgent = makeExpertAgent("standalone", "creative writing");

    const swarm = createSwarm({
      name: "meta-swarm",
      firstAgent: mw,
      relationships: [[mw, standaloneAgent]],
    });

    expect(swarm.componentType).toBe("Swarm");

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const yaml = serializer.toYaml(swarm);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Swarm");
  });
});

/* ---------- SpecializedAgent tests ---------- */

describe("Adaptive Expert: SpecializedAgent pattern", () => {
  it("should create a specialized agent with additional instructions", () => {
    const baseAgent = createAgent({
      name: "base-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a helpful assistant for {{domain}}.",
    });

    const specParams = createAgentSpecializationParameters({
      name: "finance-spec",
      additionalInstructions:
        "Focus on {{market}} trends and always cite sources from {{source}}.",
    });

    const specializedAgent = createSpecializedAgent({
      name: "finance-expert",
      agent: baseAgent,
      agentSpecializationParameters: specParams,
    });

    expect(specializedAgent.componentType).toBe("SpecializedAgent");
    expect(specializedAgent.name).toBe("finance-expert");
    // Should merge inputs from base agent and spec params
    const inputTitles = specializedAgent.inputs!.map(
      (i: { title: string }) => i.title,
    );
    expect(inputTitles).toContain("domain");
    expect(inputTitles).toContain("market");
    expect(inputTitles).toContain("source");
  });

  it("should infer specialization parameter inputs from template", () => {
    const specParams = createAgentSpecializationParameters({
      name: "spec",
      additionalInstructions: "Focus on {{area}} with {{depth}} analysis.",
    });

    expect(specParams.inputs).toBeDefined();
    const inputTitles = specParams.inputs!.map(
      (i: { title: string }) => i.title,
    );
    expect(inputTitles).toContain("area");
    expect(inputTitles).toContain("depth");
  });

  it("should support additional tools in specialization", () => {
    const baseAgent = createAgent({
      name: "base",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });

    const tool = createServerTool({
      name: "extra-tool",
      inputs: [stringProperty({ title: "query" })],
    });

    const specParams = createAgentSpecializationParameters({
      name: "spec",
      additionalTools: [tool],
    });

    const specialized = createSpecializedAgent({
      name: "specialized",
      agent: baseAgent,
      agentSpecializationParameters: specParams,
    });

    expect(specialized.componentType).toBe("SpecializedAgent");
    expect(
      specialized.agentSpecializationParameters.additionalTools,
    ).toHaveLength(1);
  });

  it("should deduplicate inputs from base agent and specialization", () => {
    const baseAgent = createAgent({
      name: "base",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful for {{shared_topic}}.",
    });

    const specParams = createAgentSpecializationParameters({
      name: "spec",
      additionalInstructions: "Be brief about {{shared_topic}} and {{extra}}.",
    });

    const specialized = createSpecializedAgent({
      name: "specialized-agent",
      agent: baseAgent,
      agentSpecializationParameters: specParams,
    });

    // shared_topic appears in both but should only appear once after deduplication
    const inputTitles = specialized.inputs!.map(
      (i: { title: string }) => i.title,
    );
    expect(inputTitles).toContain("shared_topic");
    expect(inputTitles).toContain("extra");
    // should be deduplicated
    const sharedCount = inputTitles.filter((t) => t === "shared_topic").length;
    expect(sharedCount).toBe(1);
  });
});
