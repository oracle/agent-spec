/**
 * SerializationContext - handles the recursive serialization of components.
 *
 * Manages camelCase -> snake_case conversion, component referencing,
 * sensitive field exclusion, version-gated field exclusion, and key ordering.
 */
import type { AgentSpecVersion } from "../versioning.js";
import { AGENTSPEC_VERSION_FIELD_NAME, CURRENT_VERSION, versionLt } from "../versioning.js";
import { isComponent, type ComponentBase } from "../component.js";
import type { Property } from "../property.js";
import { isSensitiveField } from "../sensitive-field.js";
import { isBuiltinComponentType } from "../component-registry.js";
import type { ComponentSerializationPlugin } from "./serialization-plugin.js";
import type { ComponentAsDict } from "./types.js";
import { computeReferencingStructure } from "./referencing.js";
import { VERSION_GATED_FIELDS } from "./version-gates.js";

/**
 * Convert camelCase to snake_case.
 * Handles standard camelCase and common abbreviation patterns (e.g. "mTLS" -> "m_tls").
 * Only designed for field names used in the Agent Spec schema — not a general-purpose converter.
 */
export function camelToSnake(str: string): string {
  return str
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1_$2")
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase();
}

/**
 * Convert snake_case to camelCase.
 * Only handles standard lowercase snake_case (e.g. "some_field" -> "someField").
 * Not a general-purpose converter — uppercase segments after underscores are not matched.
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z0-9])/g, (_, letter: string) =>
    letter.toUpperCase(),
  );
}

/** Fields that should never be transformed between camelCase/snake_case */
const NEVER_TRANSFORM_FIELDS = new Set([
  "$component_ref",
  "$referenced_components",
  "component_type",
  "agentspec_version",
  "component_plugin_name",
  "component_plugin_version",
]);

/** Priority keys for ordering serialized output */
const PRIORITY_KEYS = [
  "component_type",
  AGENTSPEC_VERSION_FIELD_NAME,
  "id",
  "name",
  "description",
];

/** Check if a value looks like a Property (has jsonSchema, title) */
function isProperty(value: unknown): value is Property {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    "jsonSchema" in obj &&
    typeof obj["jsonSchema"] === "object" &&
    "title" in obj &&
    typeof obj["title"] === "string"
  );
}

export class SerializationContext {
  agentspecVersion: AgentSpecVersion;
  camelCase: boolean;
  private componentTypesToPlugins: Map<string, ComponentSerializationPlugin>;
  private resolvedComponents: Map<string, ComponentAsDict> = new Map();
  private referencingStructure: Record<string, string> = {};
  private componentsIdMapping: Map<string, string>;

  constructor(
    plugins: ComponentSerializationPlugin[],
    targetVersion?: AgentSpecVersion,
    resolvedComponents?: Map<string, ComponentAsDict>,
    componentsIdMapping?: Map<string, string>,
    camelCase?: boolean,
  ) {
    this.agentspecVersion = targetVersion ?? CURRENT_VERSION;
    this.camelCase = camelCase ?? false;
    this.componentTypesToPlugins = this.buildComponentTypesToPlugins(plugins);
    this.resolvedComponents = resolvedComponents ?? new Map();
    this.componentsIdMapping = componentsIdMapping ?? new Map();
  }

  private buildComponentTypesToPlugins(
    plugins: ComponentSerializationPlugin[],
  ): Map<string, ComponentSerializationPlugin> {
    const map = new Map<string, ComponentSerializationPlugin>();
    for (const plugin of plugins) {
      for (const ct of plugin.supportedComponentTypes()) {
        if (map.has(ct)) {
          throw new Error(
            `Multiple plugins handle serialization of component type "${ct}". ` +
              "Remove duplicate plugins.",
          );
        }
        map.set(ct, plugin);
      }
    }
    return map;
  }

  /** Serialize a field value. Handles nested components, properties, arrays, etc. */
  dumpField(value: unknown): unknown {
    if (value === null || value === undefined) {
      return null;
    }
    if (isComponent(value)) {
      return this.dumpComponentToDict(value);
    }
    if (isProperty(value)) {
      return value.jsonSchema;
    }
    if (Array.isArray(value)) {
      return value.map((item) => this.dumpField(item));
    }
    if (typeof value === "object" && value !== null) {
      // Generic object - preserve keys as-is (user data, configuration, etc.)
      const obj = value as Record<string, unknown>;
      const result: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(obj)) {
        result[k] = this.dumpField(v);
      }
      return result;
    }
    // Primitives (string, number, boolean)
    return value;
  }

  /**
   * Serialize a LlmGenerationConfig-like object.
   * Converts keys to snake_case and excludes null/undefined values.
   * Called by the builtin serialization plugin for known model fields.
   */
  dumpModelObject(
    obj: Record<string, unknown>,
    excludeNulls: boolean,
  ): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj)) {
      if (excludeNulls && (value === null || value === undefined)) continue;
      const outKey = this.camelCase ? key : camelToSnake(key);
      result[outKey] = this.dumpField(value);
    }
    return result;
  }

  /** Serialize a component to a dict, handling referencing */
  dumpComponentToDict(component: ComponentBase): ComponentAsDict {
    const componentId = component.id;
    const mappedId =
      this.componentsIdMapping.get(componentId) ?? componentId;

    if (!this.resolvedComponents.has(mappedId)) {
      const componentType = component.componentType;
      const plugin = this.componentTypesToPlugins.get(componentType);
      if (!plugin) {
        throw new Error(
          `No plugin to serialize component type "${componentType}"`,
        );
      }

      const componentDump = plugin.serialize(component, this);
      componentDump["component_type"] = component.componentType;

      if (!isBuiltinComponentType(componentType)) {
        componentDump["component_plugin_name"] = plugin.pluginName;
        componentDump["component_plugin_version"] = plugin.pluginVersion;
      }

      // Attach $referenced_components for children that should be referenced at this level
      const referencedComponentIds: string[] = [];
      for (const [refId, parentId] of Object.entries(
        this.referencingStructure,
      )) {
        if (parentId === componentId && !this.componentsIdMapping.has(refId)) {
          referencedComponentIds.push(refId);
        }
      }
      if (referencedComponentIds.length > 0) {
        const refs: Record<string, ComponentAsDict> = {};
        for (const refId of referencedComponentIds) {
          const resolved = this.resolvedComponents.get(refId);
          if (resolved) {
            refs[refId] = resolved;
          }
        }
        componentDump["$referenced_components"] = refs;
      }

      this.resolvedComponents.set(componentId, componentDump);
    }

    // If this component should be referenced (used in multiple places) or
    // is disaggregated, return a $component_ref pointer
    const isReferenced = componentId in this.referencingStructure;
    const isDisaggregated = this.componentsIdMapping.has(componentId);
    if (isReferenced || isDisaggregated) {
      return { $component_ref: mappedId };
    }

    return this.resolvedComponents.get(mappedId)!;
  }

  /** Make output dict look nicer by ordering priority keys first */
  makeOrderedDict(obj: unknown): unknown {
    if (typeof obj === "object" && obj !== null && !Array.isArray(obj)) {
      const dict = obj as Record<string, unknown>;
      const ordered: Record<string, unknown> = {};

      // Priority keys first (recurse values for consistency)
      for (const key of PRIORITY_KEYS) {
        if (key in dict) {
          ordered[key] = this.makeOrderedDict(dict[key]);
        }
      }
      // Remaining keys
      for (const [key, value] of Object.entries(dict)) {
        if (!PRIORITY_KEYS.includes(key)) {
          ordered[key] = this.makeOrderedDict(value);
        }
      }
      return ordered;
    }
    if (Array.isArray(obj)) {
      return obj.map((item) => this.makeOrderedDict(item));
    }
    return obj;
  }

  /** Top-level serialization entry point */
  saveToDict(
    component: ComponentBase,
    agentspecVersion?: AgentSpecVersion,
  ): ComponentAsDict {
    this.agentspecVersion = agentspecVersion ?? CURRENT_VERSION;
    this.referencingStructure = computeReferencingStructure(component);

    const modelDump = this.dumpField(component) as ComponentAsDict;
    modelDump[AGENTSPEC_VERSION_FIELD_NAME] = this.agentspecVersion;

    return this.makeOrderedDict(modelDump) as ComponentAsDict;
  }

  /** Check if a field should be excluded for the current version */
  isFieldVersionGated(componentType: string, fieldName: string): boolean {
    const gatedFields = VERSION_GATED_FIELDS[componentType];
    if (!gatedFields) return false;

    // Check if the entire component is version-gated
    const selfGate = gatedFields["_self"];
    if (selfGate && versionLt(this.agentspecVersion, selfGate)) {
      return true;
    }

    const minVersion = gatedFields[fieldName];
    if (!minVersion) return false;
    return versionLt(this.agentspecVersion, minVersion);
  }

  /** Check if a field is sensitive and should be excluded */
  isFieldSensitive(componentType: string, fieldName: string): boolean {
    return isSensitiveField(componentType, fieldName);
  }

  /** Convert a camelCase field name to the appropriate serialized form */
  toSerializedFieldName(fieldName: string): string {
    if (this.camelCase) return fieldName;
    if (NEVER_TRANSFORM_FIELDS.has(fieldName)) return fieldName;
    return camelToSnake(fieldName);
  }
}
