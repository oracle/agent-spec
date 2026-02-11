import { describe, it, expect } from "vitest";
import {
  stringProperty,
  booleanProperty,
  integerProperty,
  numberProperty,
  nullProperty,
  unionProperty,
  listProperty,
  dictProperty,
  objectProperty,
  propertiesHaveSameType,
  propertyIsCastableTo,
} from "../src/index.js";

describe("stringProperty", () => {
  it("should create a string property", () => {
    const p = stringProperty({ title: "name" });
    expect(p.title).toBe("name");
    expect(p.type).toBe("string");
    expect(p.jsonSchema).toEqual({ title: "name", type: "string" });
  });

  it("should include description and default", () => {
    const p = stringProperty({
      title: "greeting",
      description: "A greeting message",
      default: "hello",
    });
    expect(p.description).toBe("A greeting message");
    expect(p.default).toBe("hello");
    expect(p.jsonSchema["description"]).toBe("A greeting message");
    expect(p.jsonSchema["default"]).toBe("hello");
  });
});

describe("booleanProperty", () => {
  it("should create a boolean property", () => {
    const p = booleanProperty({ title: "active" });
    expect(p.type).toBe("boolean");
    expect(p.jsonSchema["type"]).toBe("boolean");
  });

  it("should include default value", () => {
    const p = booleanProperty({ title: "enabled", default: true });
    expect(p.default).toBe(true);
    expect(p.jsonSchema["default"]).toBe(true);
  });
});

describe("integerProperty", () => {
  it("should create an integer property", () => {
    const p = integerProperty({ title: "count" });
    expect(p.type).toBe("integer");
    expect(p.jsonSchema["type"]).toBe("integer");
  });

  it("should include default value", () => {
    const p = integerProperty({ title: "count", default: 42 });
    expect(p.default).toBe(42);
  });
});

describe("numberProperty", () => {
  it("should create a number property", () => {
    const p = numberProperty({ title: "score" });
    expect(p.type).toBe("number");
    expect(p.jsonSchema["type"]).toBe("number");
  });
});

describe("nullProperty", () => {
  it("should create a null property", () => {
    const p = nullProperty({ title: "empty" });
    expect(p.type).toBe("null");
    expect(p.jsonSchema["type"]).toBe("null");
  });
});

describe("unionProperty", () => {
  it("should create a union property with anyOf", () => {
    const strProp = stringProperty({ title: "val" });
    const nullProp = nullProperty({ title: "val" });
    const p = unionProperty({
      title: "maybe_string",
      anyOf: [strProp, nullProp],
    });
    expect(p.title).toBe("maybe_string");
    expect(p.jsonSchema["anyOf"]).toEqual([
      { title: "val", type: "string" },
      { title: "val", type: "null" },
    ]);
  });

  it("should include a default value", () => {
    const p = unionProperty({
      title: "opt",
      anyOf: [stringProperty({ title: "x" }), nullProperty({ title: "x" })],
      default: null,
    });
    expect(p.default).toBeNull();
    expect(p.jsonSchema["default"]).toBeNull();
  });
});

describe("listProperty", () => {
  it("should create an array-typed property", () => {
    const item = stringProperty({ title: "item" });
    const p = listProperty({ title: "names", itemType: item });
    expect(p.type).toBe("array");
    expect(p.jsonSchema["type"]).toBe("array");
    expect(p.jsonSchema["items"]).toEqual({ title: "item", type: "string" });
  });

  it("should support a default value", () => {
    const p = listProperty({
      title: "tags",
      itemType: stringProperty({ title: "tag" }),
      default: ["a", "b"],
    });
    expect(p.default).toEqual(["a", "b"]);
  });
});

describe("dictProperty", () => {
  it("should create an object-typed property with additionalProperties", () => {
    const valType = numberProperty({ title: "val" });
    const p = dictProperty({ title: "scores", valueType: valType });
    expect(p.type).toBe("object");
    expect(p.jsonSchema["type"]).toBe("object");
    expect(p.jsonSchema["additionalProperties"]).toEqual({
      title: "val",
      type: "number",
    });
    expect(p.jsonSchema["properties"]).toEqual({});
  });
});

describe("objectProperty", () => {
  it("should create an object-typed property with explicit properties", () => {
    const p = objectProperty({
      title: "person",
      properties: {
        name: stringProperty({ title: "name" }),
        age: integerProperty({ title: "age" }),
      },
    });
    expect(p.type).toBe("object");
    expect(p.jsonSchema["properties"]).toEqual({
      name: { title: "name", type: "string" },
      age: { title: "age", type: "integer" },
    });
  });
});

describe("Title validation", () => {
  it("should reject titles with periods", () => {
    expect(() => stringProperty({ title: "a.b" })).toThrow();
  });

  it("should reject titles with commas", () => {
    expect(() => stringProperty({ title: "a,b" })).toThrow();
  });

  it("should reject titles with curly braces", () => {
    expect(() => stringProperty({ title: "a{b}" })).toThrow();
  });

  it("should reject titles with spaces", () => {
    expect(() => stringProperty({ title: "a b" })).toThrow();
  });

  it("should reject titles with newlines", () => {
    expect(() => stringProperty({ title: "a\nb" })).toThrow();
  });

  it("should reject titles with single quotes", () => {
    expect(() => stringProperty({ title: "a'b" })).toThrow();
  });

  it("should reject titles with double quotes", () => {
    expect(() => stringProperty({ title: 'a"b' })).toThrow();
  });

  it("should accept valid titles", () => {
    expect(() => stringProperty({ title: "valid_title" })).not.toThrow();
    expect(() => stringProperty({ title: "CamelCase" })).not.toThrow();
    expect(() => stringProperty({ title: "with-dashes" })).not.toThrow();
    expect(() => stringProperty({ title: "with123numbers" })).not.toThrow();
  });
});

describe("propertiesHaveSameType", () => {
  it("should return true for same simple types", () => {
    const a = stringProperty({ title: "x" });
    const b = stringProperty({ title: "y" });
    expect(propertiesHaveSameType(a, b)).toBe(true);
  });

  it("should return false for different simple types", () => {
    const a = stringProperty({ title: "x" });
    const b = integerProperty({ title: "y" });
    expect(propertiesHaveSameType(a, b)).toBe(false);
  });

  it("should compare array item types", () => {
    const a = listProperty({
      title: "x",
      itemType: stringProperty({ title: "i" }),
    });
    const b = listProperty({
      title: "y",
      itemType: stringProperty({ title: "j" }),
    });
    expect(propertiesHaveSameType(a, b)).toBe(true);

    const c = listProperty({
      title: "z",
      itemType: integerProperty({ title: "k" }),
    });
    expect(propertiesHaveSameType(a, c)).toBe(false);
  });

  it("should compare union types bidirectionally", () => {
    const a = unionProperty({
      title: "u",
      anyOf: [stringProperty({ title: "a" }), nullProperty({ title: "b" })],
    });
    const b = unionProperty({
      title: "v",
      anyOf: [nullProperty({ title: "c" }), stringProperty({ title: "d" })],
    });
    expect(propertiesHaveSameType(a, b)).toBe(true);
  });
});

describe("propertyIsCastableTo", () => {
  it("should allow casting any type to string", () => {
    expect(
      propertyIsCastableTo(
        integerProperty({ title: "x" }),
        stringProperty({ title: "y" }),
      ),
    ).toBe(true);
    expect(
      propertyIsCastableTo(
        booleanProperty({ title: "x" }),
        stringProperty({ title: "y" }),
      ),
    ).toBe(true);
  });

  it("should allow casting between numerical types", () => {
    expect(
      propertyIsCastableTo(
        integerProperty({ title: "x" }),
        numberProperty({ title: "y" }),
      ),
    ).toBe(true);
    expect(
      propertyIsCastableTo(
        booleanProperty({ title: "x" }),
        integerProperty({ title: "y" }),
      ),
    ).toBe(true);
  });

  it("should return true for identical types", () => {
    const a = stringProperty({ title: "x" });
    const b = stringProperty({ title: "y" });
    expect(propertyIsCastableTo(a, b)).toBe(true);
  });

  it("should allow casting to untyped property", () => {
    const a = stringProperty({ title: "x" });
    const b = { jsonSchema: { title: "y" }, title: "y", type: undefined };
    expect(propertyIsCastableTo(a, b as any)).toBe(true);
  });
});
