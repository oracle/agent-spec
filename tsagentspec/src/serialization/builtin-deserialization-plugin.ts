/**
 * BuiltinsComponentDeserializationPlugin - deserializes all builtin component types.
 *
 * Reads component_type, converts snake_case fields to camelCase, resolves nested
 * components and $component_refs, then calls the appropriate factory function.
 */
import {
  BUILTIN_SCHEMA_MAP,
  BUILTIN_FACTORY_MAP,
} from "../component-registry.js";
import type { ComponentBase } from "../component.js";
import { propertyFromJsonSchema, type Property } from "../property.js";
import type { ComponentDeserializationPlugin } from "./deserialization-plugin.js";
import type { DeserializationContext } from "./deserialization-context.js";
import {
  DANGEROUS_KEYS,
  ALL_PROTOCOL_FIELDS,
  isSerializedComponent,
  isComponentRef,
  type SerializedDict,
} from "./types.js";
import { snakeToCamel } from "./serialization-context.js";

/**
 * Fields that hold Property[] values.
 * These need to be deserialized from jsonSchema dicts back to Property objects.
 */
const PROPERTY_ARRAY_FIELDS = new Set(["inputs", "outputs"]);

/**
 * Fields (camelCase) whose object values are model objects with snake_case keys
 * that need conversion. All other object values are user data with preserved keys.
 */
const MODEL_OBJECT_FIELDS = new Set(["defaultGenerationParameters"]);

/** Deserialize a jsonSchema dict into a Property */
function deserializeProperty(value: unknown): Property {
  if (value === null || typeof value !== "object") {
    throw new Error(
      `Expected property json schema dict, got ${typeof value}`,
    );
  }
  return propertyFromJsonSchema(value as Record<string, unknown>);
}

/** Convert all keys in a plain object from snake_case to camelCase */
function convertObjectKeys(
  obj: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    result[snakeToCamel(k)] = v;
  }
  return result;
}

export class BuiltinsComponentDeserializationPlugin
  implements ComponentDeserializationPlugin
{
  readonly pluginName = "BuiltinsComponentPlugin";
  readonly pluginVersion = "0.1.0";

  supportedComponentTypes(): string[] {
    return Object.keys(BUILTIN_SCHEMA_MAP);
  }

  deserialize(
    data: SerializedDict,
    context: DeserializationContext,
  ): ComponentBase {
    const componentType = context.getComponentType(data);
    const factory = BUILTIN_FACTORY_MAP[componentType];
    if (!factory) {
      throw new Error(
        `No factory function for component type "${componentType}"`,
      );
    }

    // Convert all fields from snake_case to camelCase and resolve nested components
    const opts: Record<string, unknown> = {};
    const useCamelCase = context.camelCase;
    for (const [key, value] of Object.entries(data)) {
      // Skip all protocol fields (both snake_case and camelCase forms)
      if (ALL_PROTOCOL_FIELDS.has(key)) continue;

      const camelKey = useCamelCase
        ? key
        : snakeToCamel(key);

      // Handle Property array fields (inputs, outputs)
      if (PROPERTY_ARRAY_FIELDS.has(camelKey) && Array.isArray(value)) {
        opts[camelKey] = value.map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "title" in (item as Record<string, unknown>)
          ) {
            return deserializeProperty(item);
          }
          return item;
        });
        continue;
      }

      // Handle model object fields (keys need snake_case -> camelCase)
      if (
        MODEL_OBJECT_FIELDS.has(camelKey) &&
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
      ) {
        opts[camelKey] = useCamelCase
          ? value
          : convertObjectKeys(value as Record<string, unknown>);
        continue;
      }

      // Recursively resolve the field value
      opts[camelKey] = this.resolveField(value, context);
    }

    return factory(opts);
  }

  /** Recursively resolve a field value, handling components, refs, and nested structures */
  private resolveField(
    value: unknown,
    context: DeserializationContext,
  ): unknown {
    if (value === null || value === undefined) {
      return undefined;
    }

    if (isComponentRef(value)) {
      return context.loadReference(value["$component_ref"]);
    }

    if (isSerializedComponent(value)) {
      return context.loadComponentFromDict(value);
    }

    if (Array.isArray(value)) {
      return value.map((item) => this.resolveField(item, context));
    }

    // Plain objects - preserve keys (user data like data, headers, metadata, etc.)
    if (value !== null && typeof value === "object") {
      const obj = value as Record<string, unknown>;
      const result: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(obj)) {
        if (DANGEROUS_KEYS.has(k)) continue;
        result[k] = this.resolveField(v, context);
      }
      return result;
    }

    return value;
  }
}
