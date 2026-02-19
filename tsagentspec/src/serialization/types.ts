/**
 * Shared types and protocol constants for the serialization system.
 */
import type { ComponentBase } from "../component.js";

// ---------------------------------------------------------------------------
// Typed serialized shapes
// ---------------------------------------------------------------------------

/** A serialized component in snake_case mode — has a `component_type` discriminator */
export interface SerializedComponent {
  component_type: string;
  [key: string]: unknown;
}

/** A serialized component in camelCase mode — has a `componentType` discriminator */
export interface CamelCaseSerializedComponent {
  componentType: string;
  [key: string]: unknown;
}

/** A component reference pointer */
export interface ComponentRef {
  $component_ref: string;
}

/** A complete serialized dict — either a full component, a camelCase component, or a ref */
export type SerializedDict =
  | SerializedComponent
  | CamelCaseSerializedComponent
  | ComponentRef;

/** A wrapper containing disaggregated (extracted) components for separate transport */
export interface DisaggregatedComponentsDict {
  $referenced_components: Record<string, SerializedDict>;
}

/**
 * Partial fields returned by plugins before the context adds the protocol
 * envelope (component_type, agentspec_version, etc.).
 */
export type SerializedFields = Record<string, unknown>;

// ---------------------------------------------------------------------------
// Protocol key mapping
// ---------------------------------------------------------------------------

/** Protocol field names in both naming conventions */
export const PROTOCOL_KEYS = {
  snake: {
    componentType: "component_type",
    agentspecVersion: "agentspec_version",
    componentPluginName: "component_plugin_name",
    componentPluginVersion: "component_plugin_version",
  },
  camel: {
    componentType: "componentType",
    agentspecVersion: "agentspecVersion",
    componentPluginName: "componentPluginName",
    componentPluginVersion: "componentPluginVersion",
  },
} as const;

/** Get the protocol key mapping for the given naming mode */
export function getProtocolKeys(camelCase: boolean) {
  return camelCase ? PROTOCOL_KEYS.camel : PROTOCOL_KEYS.snake;
}

/**
 * All protocol field names (both snake_case and camelCase forms).
 * Used as a single skip/filter set in serialization and deserialization.
 */
export const ALL_PROTOCOL_FIELDS = new Set([
  ...Object.values(PROTOCOL_KEYS.snake),
  ...Object.values(PROTOCOL_KEYS.camel),
  "$referenced_components",
  "$component_ref",
  "air_version", // legacy
]);

// ---------------------------------------------------------------------------
// Type guards
// ---------------------------------------------------------------------------

/** Check if a value is a serialized component dict (either naming convention) */
export function isSerializedComponent(
  value: unknown,
): value is SerializedComponent | CamelCaseSerializedComponent {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    return false;
  const obj = value as Record<string, unknown>;
  return "component_type" in obj || "componentType" in obj;
}

/** Check if a value is a $component_ref pointer */
export function isComponentRef(value: unknown): value is ComponentRef {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    return false;
  return "$component_ref" in (value as Record<string, unknown>);
}

// ---------------------------------------------------------------------------
// Other shared types
// ---------------------------------------------------------------------------

/** Maps component IDs to component objects */
export type ComponentsRegistry = Map<string, ComponentBase>;

/** Keys that must be rejected to prevent prototype pollution */
export const DANGEROUS_KEYS = new Set([
  "__proto__",
  "constructor",
  "prototype",
]);

/** Marker used during deserialization to detect circular dependencies */
export class DeserializationInProgressMarker {
  readonly __marker = "DESERIALIZATION_IN_PROGRESS";
}
