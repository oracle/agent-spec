import { describe, it, expect } from "vitest";
import {
  TEMPLATE_PLACEHOLDER_REGEXP,
  getPlaceholdersFromString,
  getPlaceholdersFromJsonObject,
  getPlaceholderPropertiesFromJsonObject,
} from "../src/index.js";

describe("TEMPLATE_PLACEHOLDER_REGEXP", () => {
  it("should match simple placeholders", () => {
    const match = "{{name}}".match(
      new RegExp(TEMPLATE_PLACEHOLDER_REGEXP.source),
    );
    expect(match).not.toBeNull();
    expect(match![1]).toBe("name");
  });

  it("should match placeholders with whitespace", () => {
    const match = "{{ name }}".match(
      new RegExp(TEMPLATE_PLACEHOLDER_REGEXP.source),
    );
    expect(match).not.toBeNull();
    expect(match![1]).toBe("name");
  });
});

describe("getPlaceholdersFromString", () => {
  it("should extract a single placeholder", () => {
    expect(getPlaceholdersFromString("Hello {{name}}!")).toEqual(["name"]);
  });

  it("should extract multiple placeholders", () => {
    const result = getPlaceholdersFromString(
      "{{greeting}} {{name}}, you are {{age}} years old",
    );
    expect(result).toContain("greeting");
    expect(result).toContain("name");
    expect(result).toContain("age");
    expect(result).toHaveLength(3);
  });

  it("should deduplicate placeholders", () => {
    const result = getPlaceholdersFromString("{{a}} and {{a}} again");
    expect(result).toEqual(["a"]);
  });

  it("should return empty array for no placeholders", () => {
    expect(getPlaceholdersFromString("no placeholders")).toEqual([]);
  });

  it("should return empty array for empty string", () => {
    expect(getPlaceholdersFromString("")).toEqual([]);
  });

  it("should handle placeholders with underscores", () => {
    expect(getPlaceholdersFromString("{{my_var}}")).toEqual(["my_var"]);
  });

  it("should handle placeholders with numbers", () => {
    expect(getPlaceholdersFromString("{{var1}}")).toEqual(["var1"]);
  });
});

describe("getPlaceholdersFromJsonObject", () => {
  it("should extract from a plain string", () => {
    expect(getPlaceholdersFromJsonObject("{{name}}")).toEqual(["name"]);
  });

  it("should extract from an array of strings", () => {
    const result = getPlaceholdersFromJsonObject(["{{a}}", "{{b}}"]);
    expect(result).toContain("a");
    expect(result).toContain("b");
  });

  it("should extract from nested objects", () => {
    const result = getPlaceholdersFromJsonObject({
      url: "http://{{host}}/api",
      data: { key: "{{token}}" },
    });
    expect(result).toContain("host");
    expect(result).toContain("token");
  });

  it("should extract from object keys", () => {
    const result = getPlaceholdersFromJsonObject({
      "{{key_name}}": "value",
    });
    expect(result).toContain("key_name");
  });

  it("should return empty for numbers", () => {
    expect(getPlaceholdersFromJsonObject(42)).toEqual([]);
  });

  it("should return empty for null", () => {
    expect(getPlaceholdersFromJsonObject(null)).toEqual([]);
  });

  it("should return empty for boolean", () => {
    expect(getPlaceholdersFromJsonObject(true)).toEqual([]);
  });
});

describe("getPlaceholderPropertiesFromJsonObject", () => {
  it("should return Property instances for each placeholder", () => {
    const props = getPlaceholderPropertiesFromJsonObject(
      "Hello {{name}}, welcome to {{place}}",
    );
    expect(props).toHaveLength(2);

    const namesProp = props.find((p) => p.title === "name");
    expect(namesProp).toBeDefined();
    expect(namesProp!.type).toBe("string");
    expect(namesProp!.jsonSchema).toEqual({ title: "name", type: "string" });

    const placeProp = props.find((p) => p.title === "place");
    expect(placeProp).toBeDefined();
    expect(placeProp!.type).toBe("string");
  });

  it("should return empty array for no placeholders", () => {
    expect(getPlaceholderPropertiesFromJsonObject("no placeholders")).toEqual(
      [],
    );
  });

  it("should handle nested object placeholders", () => {
    const props = getPlaceholderPropertiesFromJsonObject({
      url: "{{base_url}}/api",
      headers: { auth: "Bearer {{token}}" },
    });
    expect(props).toHaveLength(2);
    expect(props.map((p) => p.title).sort()).toEqual(["base_url", "token"]);
  });
});
