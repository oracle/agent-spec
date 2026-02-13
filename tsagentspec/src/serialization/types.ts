/**
 * Shared type aliases for the serialization system.
 */
import type { ComponentBase } from "../component.js";

/** A serialized component as a plain dictionary */
export type ComponentAsDict = Record<string, unknown>;

/** Maps component IDs to component objects */
export type ComponentsRegistry = Map<string, ComponentBase>;

/** Disaggregated components configuration */
export interface DisaggregatedComponentsConfig {
  rootComponent: ComponentAsDict;
  referencedComponents: ComponentAsDict[];
}

/** Keys that must be rejected to prevent prototype pollution */
export const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);

/** Marker used during deserialization to detect circular dependencies */
export class DeserializationInProgressMarker {
  readonly __marker = "DESERIALIZATION_IN_PROGRESS";
}
