/**
 * ComponentSerializationPlugin interface.
 *
 * Plugins handle serialization of specific component types.
 */
import type { ComponentBase } from "../component.js";
import type { SerializationContext } from "./serialization-context.js";
import type { SerializedFields } from "./types.js";

export interface ComponentSerializationPlugin {
  readonly pluginName: string;
  readonly pluginVersion: string;

  /** Return the component type strings this plugin can serialize */
  supportedComponentTypes(): string[];

  /** Serialize a component's fields (the context adds the protocol envelope) */
  serialize(
    component: ComponentBase,
    context: SerializationContext,
  ): SerializedFields;
}
