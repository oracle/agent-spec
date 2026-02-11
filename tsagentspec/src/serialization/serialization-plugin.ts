/**
 * ComponentSerializationPlugin interface.
 *
 * Plugins handle serialization of specific component types.
 */
import type { ComponentBase } from "../component.js";
import type { SerializationContext } from "./serialization-context.js";
import type { ComponentAsDict } from "./types.js";

export interface ComponentSerializationPlugin {
  readonly pluginName: string;
  readonly pluginVersion: string;

  /** Return the component type strings this plugin can serialize */
  supportedComponentTypes(): string[];

  /** Serialize a component to a plain dict */
  serialize(
    component: ComponentBase,
    context: SerializationContext,
  ): ComponentAsDict;
}
