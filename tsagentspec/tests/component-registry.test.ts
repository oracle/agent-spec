import { describe, it, expect } from "vitest";
import {
  BUILTIN_SCHEMA_MAP,
  BUILTIN_FACTORY_MAP,
  getSchemaForComponentType,
  isBuiltinComponentType,
  getComponentFactory,
} from "../src/component-registry.js";

describe("component-registry", () => {
  it("should have matching keys in schema and factory maps", () => {
    expect(Object.keys(BUILTIN_SCHEMA_MAP).sort()).toEqual(
      Object.keys(BUILTIN_FACTORY_MAP).sort(),
    );
  });

  it("should return the schema for a known component type", () => {
    expect(getSchemaForComponentType("Agent")).toBeDefined();
    expect(getSchemaForComponentType("Flow")).toBeDefined();
    expect(getSchemaForComponentType("ServerTool")).toBeDefined();
  });

  it("should return undefined for unknown component types", () => {
    expect(getSchemaForComponentType("NonExistent")).toBeUndefined();
    expect(getComponentFactory("NonExistent")).toBeUndefined();
  });

  it("should correctly identify builtin component types", () => {
    expect(isBuiltinComponentType("Agent")).toBe(true);
    expect(isBuiltinComponentType("Flow")).toBe(true);
    expect(isBuiltinComponentType("NonExistent")).toBe(false);
  });

  it("should return a factory function for known types", () => {
    const factory = getComponentFactory("Agent");
    expect(factory).toBeDefined();
    expect(typeof factory).toBe("function");
  });
});
