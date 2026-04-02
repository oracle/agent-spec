import { describe, it, expect } from "vitest";
import {
  createServerTool,
  stringProperty,
  integerProperty,
} from "../../src/index.js";

describe("ServerTool", () => {
  it("should create with required fields", () => {
    const tool = createServerTool({ name: "my-tool" });
    expect(tool.componentType).toBe("ServerTool");
    expect(tool.name).toBe("my-tool");
    expect(tool.requiresConfirmation).toBe(false);
  });

  it("should auto-generate an id", () => {
    const tool = createServerTool({ name: "my-tool" });
    expect(tool.id).toBeDefined();
  });

  it("should accept inputs and outputs", () => {
    const tool = createServerTool({
      name: "calc-tool",
      inputs: [
        stringProperty({ title: "expression" }),
      ],
      outputs: [
        integerProperty({ title: "result" }),
      ],
    });
    expect(tool.inputs).toHaveLength(1);
    expect(tool.inputs![0]!.title).toBe("expression");
    expect(tool.outputs).toHaveLength(1);
    expect(tool.outputs![0]!.title).toBe("result");
  });

  it("should accept requiresConfirmation", () => {
    const tool = createServerTool({
      name: "dangerous-tool",
      requiresConfirmation: true,
    });
    expect(tool.requiresConfirmation).toBe(true);
  });

  it("should accept description", () => {
    const tool = createServerTool({
      name: "my-tool",
      description: "A useful tool",
    });
    expect(tool.description).toBe("A useful tool");
  });

  it("should be frozen", () => {
    const tool = createServerTool({ name: "my-tool" });
    expect(Object.isFrozen(tool)).toBe(true);
  });
});
