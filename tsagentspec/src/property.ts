/**
 * Property system for component inputs and outputs.
 *
 * Properties wrap JSON Schema and provide typed constructors.
 * A Property serializes to its jsonSchema dict (not a wrapper).
 */
import { z } from "zod";

/** JSON Schema value type used by Agent Spec */
export type JsonSchemaValue = Record<string, unknown>;

const INVALID_TITLE_CHARS = ".,{} \n'\"";

function validateTitle(title: string): string {
  if (title.length === 0) {
    throw new Error("Property title cannot be empty");
  }
  for (const c of INVALID_TITLE_CHARS) {
    if (title.includes(c)) {
      throw new Error(
        `Titles of properties should not contain special characters or blank space. Found: '${title}'`,
      );
    }
  }
  return title;
}

function validateSchemaTitle(jsonSchema: JsonSchemaValue): void {
  const title = jsonSchema["title"];
  if (typeof title === "string") {
    validateTitle(title);
  }
  if (jsonSchema["items"] && typeof jsonSchema["items"] === "object") {
    validateSchemaTitle(jsonSchema["items"] as JsonSchemaValue);
  }
  const anyOf = jsonSchema["anyOf"];
  if (Array.isArray(anyOf)) {
    for (const inner of anyOf) {
      if (typeof inner === "object" && inner !== null) {
        validateSchemaTitle(inner as JsonSchemaValue);
      }
    }
  }
  const additionalProperties = jsonSchema["additionalProperties"];
  if (
    typeof additionalProperties === "object" &&
    additionalProperties !== null
  ) {
    validateSchemaTitle(additionalProperties as JsonSchemaValue);
  }
  const properties = jsonSchema["properties"];
  if (typeof properties === "object" && properties !== null) {
    for (const inner of Object.values(
      properties as Record<string, unknown>,
    )) {
      if (typeof inner === "object" && inner !== null) {
        validateSchemaTitle(inner as JsonSchemaValue);
      }
    }
  }
}

/** Base property Zod schema */
export const PropertySchema = z.object({
  jsonSchema: z.record(z.unknown()).default({}),
  title: z.string().min(1).default("property"),
  description: z.string().optional(),
  default: z.unknown().optional(),
  type: z.union([z.string(), z.array(z.string())]).optional(),
});

/** A Property defines an input or output of a component */
export type Property = z.infer<typeof PropertySchema>;

function buildJsonSchema(opts: Record<string, unknown>): JsonSchemaValue {
  const js: JsonSchemaValue = {};
  if ("title" in opts && opts["title"] !== undefined) js["title"] = opts["title"];
  if ("description" in opts && opts["description"] !== undefined)
    js["description"] = opts["description"];
  if ("default" in opts && opts["default"] !== undefined)
    js["default"] = opts["default"];
  if ("type" in opts && opts["type"] !== undefined) js["type"] = opts["type"];
  return js;
}

function makeProperty(
  jsonSchema: JsonSchemaValue,
  title: string,
  description?: string,
  defaultValue?: unknown,
): Property {
  validateSchemaTitle(jsonSchema);
  const p: Property = {
    jsonSchema,
    title,
    description,
    default: defaultValue,
    type: jsonSchema["type"] as string | string[] | undefined,
  };
  return Object.freeze(p);
}

/** Create a string-typed property */
export function stringProperty(opts: {
  title: string;
  description?: string;
  default?: string;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    type: "string",
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create a boolean-typed property */
export function booleanProperty(opts: {
  title: string;
  description?: string;
  default?: boolean;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    type: "boolean",
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create an integer-typed property */
export function integerProperty(opts: {
  title: string;
  description?: string;
  default?: number;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    type: "integer",
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create a number-typed property */
export function numberProperty(opts: {
  title: string;
  description?: string;
  default?: number;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    type: "number",
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create a null-typed property */
export function nullProperty(opts: {
  title: string;
  description?: string;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    type: "null",
  };
  return makeProperty(js, opts.title, opts.description);
}

/** Create a union-typed property (anyOf) */
export function unionProperty(opts: {
  title: string;
  anyOf: Property[];
  description?: string;
  default?: unknown;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    anyOf: opts.anyOf.map((p) => p.jsonSchema),
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create a list-typed property (array) */
export function listProperty(opts: {
  title: string;
  itemType: Property;
  description?: string;
  default?: unknown[];
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    items: opts.itemType.jsonSchema,
    type: "array",
  };
  return makeProperty(js, opts.title, opts.description, opts.default);
}

/** Create a dict-typed property (object with additionalProperties) */
export function dictProperty(opts: {
  title: string;
  valueType: Property;
  description?: string;
}): Property {
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    additionalProperties: opts.valueType.jsonSchema,
    properties: {},
    type: "object",
  };
  return makeProperty(js, opts.title, opts.description);
}

/** Create an object-typed property (with explicit properties) */
export function objectProperty(opts: {
  title: string;
  properties: Record<string, Property>;
  description?: string;
}): Property {
  const props: Record<string, JsonSchemaValue> = {};
  for (const [k, v] of Object.entries(opts.properties)) {
    props[k] = v.jsonSchema;
  }
  const js: JsonSchemaValue = {
    ...buildJsonSchema(opts),
    properties: props,
    type: "object",
  };
  return makeProperty(js, opts.title, opts.description);
}

/** Create a property from a raw JSON schema dict */
export function propertyFromJsonSchema(jsonSchema: JsonSchemaValue): Property {
  const title = (jsonSchema["title"] as string) || "property";
  const description = jsonSchema["description"] as string | undefined;
  const defaultValue = jsonSchema["default"];
  return makeProperty(jsonSchema, title, description, defaultValue);
}

// --- Comparison helpers ---

function normalizeUnionTypes(
  schema: JsonSchemaValue,
): JsonSchemaValue[] {
  const jsonSchemaType = schema["type"] ?? [];
  const types: string[] = typeof jsonSchemaType === "string"
    ? [jsonSchemaType]
    : Array.isArray(jsonSchemaType)
      ? (jsonSchemaType as string[])
      : [];

  const allTypes: JsonSchemaValue[] = [
    ...((schema["anyOf"] as JsonSchemaValue[]) ?? []),
  ];

  for (const t of types) {
    if (t === "array") {
      allTypes.push({ type: "array", items: schema["items"] ?? {} });
    } else if (t === "object") {
      allTypes.push({
        type: "object",
        properties: schema["properties"] ?? {},
        additionalProperties: schema["additionalProperties"] ?? false,
      });
    } else {
      allTypes.push({ type: t });
    }
  }

  return allTypes;
}

function jsonSchemasHaveSameType(
  a: JsonSchemaValue,
  b: JsonSchemaValue,
): boolean {
  if ("allOf" in a || "allOf" in b) {
    throw new Error("Support for schemas using allOf is not implemented.");
  }
  if ("oneOf" in a || "oneOf" in b) {
    throw new Error("Support for schemas using oneOf is not implemented.");
  }

  if (
    "anyOf" in a ||
    Array.isArray(a["type"]) ||
    "anyOf" in b ||
    Array.isArray(b["type"])
  ) {
    const aTypes = normalizeUnionTypes(a);
    const bTypes = normalizeUnionTypes(b);
    for (const at of aTypes) {
      if (!bTypes.some((bt) => jsonSchemasHaveSameType(at, bt))) return false;
    }
    for (const bt of bTypes) {
      if (!aTypes.some((at) => jsonSchemasHaveSameType(at, bt))) return false;
    }
    return true;
  }

  if (a["type"] !== b["type"]) return false;

  if ("items" in a || "items" in b) {
    if (
      !jsonSchemasHaveSameType(
        (a["items"] as JsonSchemaValue) ?? {},
        (b["items"] as JsonSchemaValue) ?? {},
      )
    )
      return false;
  }

  if ("properties" in a || "properties" in b) {
    const aProps = (a["properties"] ?? {}) as Record<string, JsonSchemaValue>;
    const bProps = (b["properties"] ?? {}) as Record<string, JsonSchemaValue>;
    if (
      Object.keys(aProps).sort().join(",") !==
      Object.keys(bProps).sort().join(",")
    )
      return false;
    for (const key of Object.keys(aProps)) {
      if (!jsonSchemasHaveSameType(aProps[key]!, bProps[key]!)) return false;
    }
  }

  if ("additionalProperties" in a || "additionalProperties" in b) {
    const aAP = a["additionalProperties"] ?? {};
    const bAP = b["additionalProperties"] ?? {};
    if (typeof aAP === "boolean" || typeof bAP === "boolean") {
      return aAP === bAP;
    }
    if (
      !jsonSchemasHaveSameType(
        aAP as JsonSchemaValue,
        bAP as JsonSchemaValue,
      )
    )
      return false;
  }

  return true;
}

/** Check if two properties have the same type */
export function propertiesHaveSameType(a: Property, b: Property): boolean {
  return jsonSchemasHaveSameType(a.jsonSchema, b.jsonSchema);
}

function jsonSchemaIsCastableTo(
  a: JsonSchemaValue,
  b: JsonSchemaValue,
): boolean {
  if ("allOf" in a || "allOf" in b) {
    throw new Error("Support for schemas using allOf is not implemented.");
  }
  if ("oneOf" in a || "oneOf" in b) {
    throw new Error("Support for schemas using oneOf is not implemented.");
  }
  if (JSON.stringify(a) === JSON.stringify(b)) return true;
  if (!("type" in b) && !("anyOf" in b)) return true;
  if (b["type"] === "string") return true;

  if (
    "anyOf" in a ||
    Array.isArray(a["type"]) ||
    "anyOf" in b ||
    Array.isArray(b["type"])
  ) {
    const aTypes = normalizeUnionTypes(a);
    const bTypes = normalizeUnionTypes(b);
    for (const at of aTypes) {
      if (!bTypes.some((bt) => jsonSchemaIsCastableTo(at, bt))) return false;
    }
    return true;
  }

  const numericalTypes = new Set(["number", "integer", "boolean"]);
  if (
    numericalTypes.has(a["type"] as string) &&
    numericalTypes.has(b["type"] as string)
  )
    return true;

  if (a["type"] === "array" && b["type"] === "array") {
    return jsonSchemaIsCastableTo(
      (a["items"] as JsonSchemaValue) ?? {},
      (b["items"] as JsonSchemaValue) ?? {},
    );
  }

  if (a["type"] === "object" && b["type"] === "object") {
    const propsA = (a["properties"] ?? {}) as Record<string, JsonSchemaValue>;
    const propsB = (b["properties"] ?? {}) as Record<string, JsonSchemaValue>;
    for (const [name, propType] of Object.entries(propsB)) {
      if (!(name in propsA) || !jsonSchemaIsCastableTo(propsA[name]!, propType))
        return false;
    }
    const aAP = a["additionalProperties"] ?? {};
    const bAP = b["additionalProperties"] ?? {};
    if (typeof aAP === "boolean" || typeof bAP === "boolean") {
      return aAP === bAP;
    }
    return jsonSchemaIsCastableTo(
      aAP as JsonSchemaValue,
      bAP as JsonSchemaValue,
    );
  }

  return false;
}

/** Check if property a can be cast to the type of property b */
export function propertyIsCastableTo(a: Property, b: Property): boolean {
  return jsonSchemaIsCastableTo(a.jsonSchema, b.jsonSchema);
}

/** Deduplicate properties with same title and type */
export function deduplicatePropertiesByTitleAndType(
  properties: Property[],
): Property[] {
  const byTitle = new Map<string, Property[]>();
  for (const p of properties) {
    const list = byTitle.get(p.title) ?? [];
    list.push(p);
    byTitle.set(p.title, list);
  }
  const result: Property[] = [];
  for (const propList of byTitle.values()) {
    const distinct: Property[] = [];
    for (const p of propList) {
      if (!distinct.some((d) => jsonSchemasHaveSameType(p.jsonSchema, d.jsonSchema))) {
        distinct.push(p);
      }
    }
    result.push(...distinct);
  }
  return result;
}
