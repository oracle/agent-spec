/**
 * ComponentDeserializationPlugin interface.
 *
 * Plugins handle deserialization of specific component types.
 */
import type { ComponentBase } from "../component.js";
import type { DeserializationContext } from "./deserialization-context.js";
import type { SerializedDict } from "./types.js";

export interface ComponentDeserializationPlugin {
  readonly pluginName: string;
  readonly pluginVersion: string;

  /** Return the component type strings this plugin can deserialize */
  supportedComponentTypes(): string[];

  /** Deserialize a serialized component dict to a component */
  deserialize(
    data: SerializedDict,
    context: DeserializationContext,
  ): ComponentBase;
}
