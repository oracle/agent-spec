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

/** Marker used during deserialization to detect circular dependencies */
export class DeserializationInProgressMarker {
  readonly __marker = "DESERIALIZATION_IN_PROGRESS";
}
