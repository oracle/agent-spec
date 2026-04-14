import { describe, it, expect } from "vitest";
import { ToolBaseSchema } from "../../src/index.js";

describe("ToolBase", () => {
  it("should default requiresConfirmation to false", () => {
    const result = ToolBaseSchema.parse({
      name: "test-tool",
      componentType: "ServerTool",
    });
    expect(result.requiresConfirmation).toBe(false);
  });

  it("should accept requiresConfirmation=true", () => {
    const result = ToolBaseSchema.parse({
      name: "test-tool",
      componentType: "ServerTool",
      requiresConfirmation: true,
    });
    expect(result.requiresConfirmation).toBe(true);
  });

  it("should auto-generate an id", () => {
    const result = ToolBaseSchema.parse({
      name: "test-tool",
      componentType: "ServerTool",
    });
    expect(result.id).toBeDefined();
    expect(result.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it("should default metadata to empty object", () => {
    const result = ToolBaseSchema.parse({
      name: "test-tool",
      componentType: "ServerTool",
    });
    expect(result.metadata).toEqual({});
  });
});
