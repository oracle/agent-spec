import { describe, it, expect } from "vitest";
import { ComponentBaseSchema, ComponentWithIOSchema } from "../src/index.js";

describe("ComponentBaseSchema", () => {
  it("should parse a valid component", () => {
    const result = ComponentBaseSchema.parse({
      name: "test-component",
      componentType: "Agent",
    });
    expect(result.name).toBe("test-component");
    expect(result.componentType).toBe("Agent");
    expect(result.id).toBeDefined();
    expect(result.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(result.metadata).toEqual({});
  });

  it("should auto-generate a UUID for id", () => {
    const a = ComponentBaseSchema.parse({
      name: "a",
      componentType: "Agent",
    });
    const b = ComponentBaseSchema.parse({
      name: "b",
      componentType: "Agent",
    });
    expect(a.id).not.toBe(b.id);
  });

  it("should accept a custom id", () => {
    const customId = "550e8400-e29b-41d4-a716-446655440000";
    const result = ComponentBaseSchema.parse({
      name: "test",
      componentType: "Agent",
      id: customId,
    });
    expect(result.id).toBe(customId);
  });

  it("should reject an invalid UUID", () => {
    expect(() =>
      ComponentBaseSchema.parse({
        name: "test",
        componentType: "Agent",
        id: "not-a-uuid",
      }),
    ).toThrow();
  });

  it("should accept optional description", () => {
    const result = ComponentBaseSchema.parse({
      name: "test",
      componentType: "Agent",
      description: "A test component",
    });
    expect(result.description).toBe("A test component");
  });

  it("should default description to undefined", () => {
    const result = ComponentBaseSchema.parse({
      name: "test",
      componentType: "Agent",
    });
    expect(result.description).toBeUndefined();
  });

  it("should accept custom metadata", () => {
    const result = ComponentBaseSchema.parse({
      name: "test",
      componentType: "Agent",
      metadata: { key: "value", nested: { a: 1 } },
    });
    expect(result.metadata).toEqual({ key: "value", nested: { a: 1 } });
  });

  it("should default metadata to empty object", () => {
    const result = ComponentBaseSchema.parse({
      name: "test",
      componentType: "Agent",
    });
    expect(result.metadata).toEqual({});
  });

  it("should require a name", () => {
    expect(() =>
      ComponentBaseSchema.parse({ componentType: "Agent" }),
    ).toThrow();
  });
});

describe("ComponentWithIOSchema", () => {
  it("should parse with inputs and outputs", () => {
    const result = ComponentWithIOSchema.parse({
      name: "io-test",
      componentType: "Agent",
      inputs: [
        {
          jsonSchema: { title: "x", type: "string" },
          title: "x",
          type: "string",
        },
      ],
      outputs: [
        {
          jsonSchema: { title: "y", type: "integer" },
          title: "y",
          type: "integer",
        },
      ],
    });
    expect(result.inputs).toHaveLength(1);
    expect(result.inputs![0]!.title).toBe("x");
    expect(result.outputs).toHaveLength(1);
    expect(result.outputs![0]!.title).toBe("y");
  });

  it("should default inputs and outputs to undefined", () => {
    const result = ComponentWithIOSchema.parse({
      name: "test",
      componentType: "Agent",
    });
    expect(result.inputs).toBeUndefined();
    expect(result.outputs).toBeUndefined();
  });
});
