import { describe, it, expect } from "vitest";
import {
  createRemoteAgent,
  stringProperty,
  integerProperty,
} from "../../src/index.js";

describe("RemoteAgent", () => {
  it("should create with required fields", () => {
    const agent = createRemoteAgent({ name: "remote-1" });
    expect(agent.componentType).toBe("RemoteAgent");
    expect(agent.name).toBe("remote-1");
  });

  it("should auto-generate an id", () => {
    const agent = createRemoteAgent({ name: "remote-1" });
    expect(agent.id).toBeDefined();
    expect(agent.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it("should accept a custom id", () => {
    const id = "550e8400-e29b-41d4-a716-446655440000";
    const agent = createRemoteAgent({ name: "remote-1", id });
    expect(agent.id).toBe(id);
  });

  it("should accept description and metadata", () => {
    const agent = createRemoteAgent({
      name: "remote-1",
      description: "A remote agent",
      metadata: { key: "value" },
    });
    expect(agent.description).toBe("A remote agent");
    expect(agent.metadata).toEqual({ key: "value" });
  });

  it("should accept inputs and outputs", () => {
    const agent = createRemoteAgent({
      name: "remote-1",
      inputs: [stringProperty({ title: "query" })],
      outputs: [integerProperty({ title: "count" })],
    });
    expect(agent.inputs).toHaveLength(1);
    expect(agent.inputs![0]!.title).toBe("query");
    expect(agent.outputs).toHaveLength(1);
    expect(agent.outputs![0]!.title).toBe("count");
  });

  it("should be frozen", () => {
    const agent = createRemoteAgent({ name: "remote-1" });
    expect(Object.isFrozen(agent)).toBe(true);
  });
});
