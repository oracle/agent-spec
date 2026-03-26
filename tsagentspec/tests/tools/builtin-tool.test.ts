import { describe, it, expect } from "vitest";
import { createBuiltinTool } from "../../src/index.js";

describe("BuiltinTool", () => {
  it("should create with required fields", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
    });
    expect(tool.componentType).toBe("BuiltinTool");
    expect(tool.name).toBe("code-exec");
    expect(tool.toolType).toBe("code_execution");
  });

  it("should accept configuration", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      configuration: { language: "python", timeout: 30 },
    });
    expect(tool.configuration).toEqual({ language: "python", timeout: 30 });
  });

  it("should accept executorName as string", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      executorName: "python-executor",
    });
    expect(tool.executorName).toBe("python-executor");
  });

  it("should accept executorName as string array", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      executorName: ["exec1", "exec2"],
    });
    expect(tool.executorName).toEqual(["exec1", "exec2"]);
  });

  it("should accept toolVersion", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      toolVersion: "1.0.0",
    });
    expect(tool.toolVersion).toBe("1.0.0");
  });

  it("should auto-generate an id", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
    });
    expect(tool.id).toBeDefined();
  });

  it("should be frozen", () => {
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
    });
    expect(Object.isFrozen(tool)).toBe(true);
  });
});
