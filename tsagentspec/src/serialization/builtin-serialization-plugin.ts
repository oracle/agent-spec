/**
 * BuiltinsComponentSerializationPlugin - serializes all builtin component types.
 *
 * Iterates all fields of a component, calls dumpField on each, excludes
 * sensitive and version-gated fields, and converts field names to snake_case.
 */
import { BUILTIN_SCHEMA_MAP } from "../component-registry.js";
import type { ComponentBase } from "../component.js";
import type { ComponentSerializationPlugin } from "./serialization-plugin.js";
import type { SerializationContext } from "./serialization-context.js";
import type { ComponentAsDict } from "./types.js";

/** Fields that are internal and should not appear in serialized output */
const EXCLUDED_FIELDS = new Set(["componentType"]);

/**
 * Fields that contain model objects (not components, not user data) that need
 * their keys converted to snake_case. Maps fieldName -> whether to exclude nulls.
 */
const MODEL_OBJECT_FIELDS: Record<string, boolean> = {
  defaultGenerationParameters: true, // LlmGenerationConfig - exclude nulls
};

export class BuiltinsComponentSerializationPlugin
  implements ComponentSerializationPlugin
{
  readonly pluginName = "BuiltinsComponentPlugin";
  readonly pluginVersion = "0.1.0";

  supportedComponentTypes(): string[] {
    return Object.keys(BUILTIN_SCHEMA_MAP);
  }

  serialize(
    component: ComponentBase,
    context: SerializationContext,
  ): ComponentAsDict {
    const serialized: ComponentAsDict = {};
    const componentType = component.componentType;
    const obj = component as unknown as Record<string, unknown>;

    for (const [fieldName, fieldValue] of Object.entries(obj)) {
      // Skip internal fields
      if (EXCLUDED_FIELDS.has(fieldName)) continue;

      // Skip sensitive fields
      if (context.isFieldSensitive(componentType, fieldName)) continue;

      // Skip version-gated fields
      if (context.isFieldVersionGated(componentType, fieldName)) continue;

      const snakeName = context.toSerializedFieldName(fieldName);

      // Handle model object fields specially (convert keys, optionally exclude nulls)
      if (
        fieldName in MODEL_OBJECT_FIELDS &&
        typeof fieldValue === "object" &&
        fieldValue !== null &&
        !Array.isArray(fieldValue)
      ) {
        serialized[snakeName] = context.dumpModelObject(
          fieldValue as Record<string, unknown>,
          MODEL_OBJECT_FIELDS[fieldName]!,
        );
      } else {
        serialized[snakeName] = context.dumpField(fieldValue);
      }
    }

    return serialized;
  }
}
