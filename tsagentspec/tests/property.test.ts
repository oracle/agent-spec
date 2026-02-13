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

  it("should throw for allOf schemas", () => {
    const a = { jsonSchema: { allOf: [{ type: "string" }] }, title: "x" } as any;
    const b = stringProperty({ title: "y" });
    expect(() => propertyIsCastableTo(a, b)).toThrow(
      "Support for schemas using allOf is not implemented",
    );
  });

  it("should throw for oneOf schemas", () => {
    const a = { jsonSchema: { oneOf: [{ type: "string" }] }, title: "x" } as any;
    const b = stringProperty({ title: "y" });
    expect(() => propertyIsCastableTo(a, b)).toThrow(
      "Support for schemas using oneOf is not implemented",
    );
  });

  it("should handle union type castability", () => {
    const union = unionProperty({
      title: "u",
      anyOf: [integerProperty({ title: "a" }), booleanProperty({ title: "b" })],
    });
    // All union members are numerical, so castable to number
    expect(propertyIsCastableTo(union, numberProperty({ title: "y" }))).toBe(
      true,
    );
    // But not all are castable to null
    expect(propertyIsCastableTo(union, nullProperty({ title: "y" }))).toBe(
      false,
    );
  });

  it("should handle array item castability", () => {
    const a = listProperty({
      title: "x",
      itemType: integerProperty({ title: "i" }),
    });
    const b = listProperty({
      title: "y",
      itemType: numberProperty({ title: "j" }),
    });
    // integer items castable to number items
    expect(propertyIsCastableTo(a, b)).toBe(true);

    const c = listProperty({
      title: "z",
      itemType: stringProperty({ title: "k" }),
    });
    // integer items not castable to string items... actually string is always castable to
    // Let's test string -> integer (not castable)
    expect(propertyIsCastableTo(c, a)).toBe(false);
  });

  it("should handle object property castability", () => {
    const a = objectProperty({
      title: "x",
      properties: {
        name: stringProperty({ title: "name" }),
        age: integerProperty({ title: "age" }),
      },
    });
    const b = objectProperty({
      title: "y",
      properties: {
        name: stringProperty({ title: "name" }),
      },
    });
    // a has all properties of b, so castable
    expect(propertyIsCastableTo(a, b)).toBe(true);

    // b doesn't have "age", so not castable to a
    const c = objectProperty({
      title: "z",
      properties: {
        name: stringProperty({ title: "name" }),
        age: integerProperty({ title: "age" }),
        extra: stringProperty({ title: "extra" }),
      },
    });
    // a doesn't have "extra", so not castable to c
    expect(propertyIsCastableTo(a, c)).toBe(false);
  });

  it("should handle dict (additionalProperties) castability", () => {
    const a = dictProperty({
      title: "x",
      valueType: integerProperty({ title: "v" }),
    });
    const b = dictProperty({
      title: "y",
      valueType: numberProperty({ title: "v" }),
    });
    // integer values castable to number values
    expect(propertyIsCastableTo(a, b)).toBe(true);
  });

  it("should return false for incompatible simple types", () => {
    expect(
      propertyIsCastableTo(
        nullProperty({ title: "x" }),
        integerProperty({ title: "y" }),
      ),
    ).toBe(false);
  });

  it("should handle boolean additionalProperties in object castability", () => {
    const a = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: true },
      title: "x",
    } as any;
    const b = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: true },
      title: "y",
    } as any;
    expect(propertyIsCastableTo(a, b)).toBe(true);

    const c = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: false },
      title: "z",
    } as any;
    expect(propertyIsCastableTo(a, c)).toBe(false);
  });
});

describe("propertiesHaveSameType advanced", () => {
  it("should throw for allOf schemas", () => {
    const a = { jsonSchema: { allOf: [{ type: "string" }] }, title: "x" } as any;
    const b = stringProperty({ title: "y" });
    expect(() => propertiesHaveSameType(a, b)).toThrow(
      "Support for schemas using allOf is not implemented",
    );
  });

  it("should throw for oneOf schemas", () => {
    const a = stringProperty({ title: "x" });
    const b = { jsonSchema: { oneOf: [{ type: "string" }] }, title: "y" } as any;
    expect(() => propertiesHaveSameType(a, b)).toThrow(
      "Support for schemas using oneOf is not implemented",
    );
  });

  it("should compare object properties", () => {
    const a = objectProperty({
      title: "x",
      properties: {
        name: stringProperty({ title: "name" }),
        age: integerProperty({ title: "age" }),
      },
    });
    const b = objectProperty({
      title: "y",
      properties: {
        name: stringProperty({ title: "name" }),
        age: integerProperty({ title: "age" }),
      },
    });
    expect(propertiesHaveSameType(a, b)).toBe(true);

    const c = objectProperty({
      title: "z",
      properties: {
        name: stringProperty({ title: "name" }),
      },
    });
    // Different property keys
    expect(propertiesHaveSameType(a, c)).toBe(false);
  });

  it("should compare object properties with different value types", () => {
    const a = objectProperty({
      title: "x",
      properties: { val: stringProperty({ title: "val" }) },
    });
    const b = objectProperty({
      title: "y",
      properties: { val: integerProperty({ title: "val" }) },
    });
    // Same keys but different types
    expect(propertiesHaveSameType(a, b)).toBe(false);
  });

  it("should compare additionalProperties (object schemas)", () => {
    const a = dictProperty({
      title: "x",
      valueType: stringProperty({ title: "v" }),
    });
    const b = dictProperty({
      title: "y",
      valueType: stringProperty({ title: "v" }),
    });
    expect(propertiesHaveSameType(a, b)).toBe(true);

    const c = dictProperty({
      title: "z",
      valueType: integerProperty({ title: "v" }),
    });
    expect(propertiesHaveSameType(a, c)).toBe(false);
  });

  it("should compare additionalProperties when boolean", () => {
    const a = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: true },
      title: "x",
    } as any;
    const b = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: true },
      title: "y",
    } as any;
    expect(propertiesHaveSameType(a, b)).toBe(true);

    const c = {
      jsonSchema: { type: "object", properties: {}, additionalProperties: false },
      title: "z",
    } as any;
    expect(propertiesHaveSameType(a, c)).toBe(false);
  });

  it("should return false for mismatched union types", () => {
    const a = unionProperty({
      title: "u",
      anyOf: [
        stringProperty({ title: "a" }),
        integerProperty({ title: "b" }),
      ],
    });
    const b = unionProperty({
      title: "v",
      anyOf: [
        stringProperty({ title: "c" }),
        booleanProperty({ title: "d" }),
      ],
    });
    // a has integer but b doesn't -> not same type
    expect(propertiesHaveSameType(a, b)).toBe(false);
  });

  it("should handle schema with non-standard type field", () => {
    // When type is neither string nor array (e.g. number), normalizeUnionTypes
    // falls back to empty array for types (line 247)
    const a = {
      jsonSchema: { type: 42, anyOf: [{ type: "string" }] },
      title: "x",
    } as any;
    const b = {
      jsonSchema: { anyOf: [{ type: "string" }] },
      title: "y",
    } as any;
    expect(propertiesHaveSameType(a, b)).toBe(true);
  });

  it("should handle normalizeUnionTypes with array and object in type list", () => {
    // Multi-type schema with array and object types
    const a = {
      jsonSchema: {
        type: ["array", "object"],
        items: { type: "string" },
        properties: { name: { type: "string" } },
        additionalProperties: false,
      },
      title: "x",
    } as any;
    const b = {
      jsonSchema: {
        type: ["array", "object"],
        items: { type: "string" },
        properties: { name: { type: "string" } },
        additionalProperties: false,
      },
      title: "y",
    } as any;
    expect(propertiesHaveSameType(a, b)).toBe(true);
  });
});
