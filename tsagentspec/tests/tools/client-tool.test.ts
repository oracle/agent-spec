import { describe, it, expect } from "vitest";
import { createClientTool, stringProperty } from "../../src/index.js";

describe("ClientTool", () => {
  it("should create with required fields", () => {
    const tool = createClientTool({ name: "client-tool" });
    expect(tool.componentType).toBe("ClientTool");
    expect(tool.name).toBe("client-tool");
  });

  it("should default requiresConfirmation to false", () => {
    const tool = createClientTool({ name: "client-tool" });
    expect(tool.requiresConfirmation).toBe(false);
  });

  it("should accept inputs and outputs", () => {
    const tool = createClientTool({
      name: "user-input-tool",
      inputs: [stringProperty({ title: "prompt" })],
      outputs: [stringProperty({ title: "response" })],
    });
    expect(tool.inputs).toHaveLength(1);
    expect(tool.outputs).toHaveLength(1);
  });

  it("should be frozen", () => {
    const tool = createClientTool({ name: "client-tool" });
    expect(Object.isFrozen(tool)).toBe(true);
  });

  it("should auto-generate an id", () => {
    const tool = createClientTool({ name: "client-tool" });
    expect(tool.id).toBeDefined();
  });
});
