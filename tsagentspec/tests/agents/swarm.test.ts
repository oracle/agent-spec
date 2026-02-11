import { describe, it, expect } from "vitest";
import {
  createSwarm,
  createAgent,
  createOpenAiCompatibleConfig,
  HandoffMode,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeAgent(name: string) {
  return createAgent({
    name,
    llmConfig: makeLlmConfig(),
    systemPrompt: `You are ${name}.`,
  });
}

describe("Swarm", () => {
  it("should create with required fields", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
    });
    expect(swarm.componentType).toBe("Swarm");
    expect(swarm.name).toBe("test-swarm");
  });

  it("should default handoff to OPTIONAL", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
    });
    expect(swarm.handoff).toBe(HandoffMode.OPTIONAL);
  });

  it("should accept custom handoff mode", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
      handoff: HandoffMode.ALWAYS,
    });
    expect(swarm.handoff).toBe("always");
  });

  it("should support NEVER handoff mode", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
      handoff: HandoffMode.NEVER,
    });
    expect(swarm.handoff).toBe("never");
  });

  it("should accept multiple relationships", () => {
    const a1 = makeAgent("a1");
    const a2 = makeAgent("a2");
    const a3 = makeAgent("a3");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: a1,
      relationships: [
        [a1, a2],
        [a2, a3],
        [a3, a1],
      ],
    });
    expect(swarm.relationships).toHaveLength(3);
  });

  it("should be frozen", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
    });
    expect(Object.isFrozen(swarm)).toBe(true);
  });

  it("should auto-generate an id", () => {
    const agent1 = makeAgent("agent1");
    const agent2 = makeAgent("agent2");
    const swarm = createSwarm({
      name: "test-swarm",
      firstAgent: agent1,
      relationships: [[agent1, agent2]],
    });
    expect(swarm.id).toBeDefined();
  });
});

describe("HandoffMode", () => {
  it("should define all modes", () => {
    expect(HandoffMode.NEVER).toBe("never");
    expect(HandoffMode.OPTIONAL).toBe("optional");
    expect(HandoffMode.ALWAYS).toBe("always");
  });
});
