import { describe, it, expect } from "vitest";
import {
  createManagerWorkers,
  createAgent,
  createOpenAiCompatibleConfig,
  numberProperty,
  stringProperty,
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

describe("ManagerWorkers", () => {
  it("should create with required fields", () => {
    const manager = makeAgent("manager");
    const worker1 = makeAgent("worker1");
    const worker2 = makeAgent("worker2");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [worker1, worker2],
    });
    expect(mw.componentType).toBe("ManagerWorkers");
    expect(mw.name).toBe("test-mw");
  });

  it("should have the group manager set", () => {
    const manager = makeAgent("manager");
    const worker = makeAgent("worker");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [worker],
    });
    expect((mw.groupManager as Record<string, unknown>)["name"]).toBe(
      "manager",
    );
  });

  it("should have the workers set", () => {
    const manager = makeAgent("manager");
    const w1 = makeAgent("w1");
    const w2 = makeAgent("w2");
    const w3 = makeAgent("w3");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [w1, w2, w3],
    });
    expect(mw.workers).toHaveLength(3);
  });

  it("should auto-generate an id", () => {
    const manager = makeAgent("manager");
    const worker = makeAgent("worker");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [worker],
    });
    expect(mw.id).toBeDefined();
  });

  it("should be frozen", () => {
    const manager = makeAgent("manager");
    const worker = makeAgent("worker");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [worker],
    });
    expect(Object.isFrozen(mw)).toBe(true);
  });

  it("should accept description and metadata", () => {
    const manager = makeAgent("manager");
    const worker = makeAgent("worker");
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [worker],
      description: "A manager-workers setup",
      metadata: { team: "alpha" },
    });
    expect(mw.description).toBe("A manager-workers setup");
    expect(mw.metadata).toEqual({ team: "alpha" });
  });

  it("should reject empty workers", () => {
    const manager = makeAgent("manager");
    expect(() =>
      createManagerWorkers({
        name: "test-mw",
        groupManager: manager,
        workers: [],
      }),
    ).toThrow("Cannot define a ManagerWorkers with no worker");
  });

  it("should reject manager as worker", () => {
    const manager = makeAgent("manager");
    expect(() =>
      createManagerWorkers({
        name: "test-mw",
        groupManager: manager,
        workers: [manager],
      }),
    ).toThrow("Group manager cannot be a worker.");
  });

  it("should infer the group manager's inputs and outputs", () => {
    const topic = stringProperty({ title: "topic" });
    const answer = stringProperty({ title: "answer" });
    const manager = createAgent({
      name: "manager",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Manage the team.",
      inputs: [topic],
      outputs: [answer],
    });
    const mw = createManagerWorkers({
      name: "test-mw",
      groupManager: manager,
      workers: [makeAgent("worker")],
    });

    expect(mw.inputs).toEqual([topic]);
    expect(mw.outputs).toEqual([answer]);
  });

  it("should reject explicit I/O that differs from the group manager", () => {
    const manager = createAgent({
      name: "manager",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Manage the team.",
      outputs: [stringProperty({ title: "answer" })],
    });

    expect(() =>
      createManagerWorkers({
        name: "test-mw",
        groupManager: manager,
        workers: [makeAgent("worker")],
        outputs: [numberProperty({ title: "answer" })],
      }),
    ).toThrow("outputs of a ManagerWorkers must match");
  });
});
