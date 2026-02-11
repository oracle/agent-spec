/**
 * Serialization system barrel exports.
 */

// Type aliases
export type {
  ComponentAsDict,
  ComponentsRegistry,
  DisaggregatedComponentsConfig,
} from "./types.js";

// Plugin interfaces
export type { ComponentSerializationPlugin } from "./serialization-plugin.js";
export type { ComponentDeserializationPlugin } from "./deserialization-plugin.js";

// Context classes
export { SerializationContext, camelToSnake, snakeToCamel } from "./serialization-context.js";
export { DeserializationContext } from "./deserialization-context.js";

// Builtin plugins
export { BuiltinsComponentSerializationPlugin } from "./builtin-serialization-plugin.js";
export { BuiltinsComponentDeserializationPlugin } from "./builtin-deserialization-plugin.js";

// Referencing
export {
  computeReferencingStructure,
  getChildrenFromFieldValue,
  getAllDirectChildren,
} from "./referencing.js";

// Version gates
export { VERSION_GATED_FIELDS } from "./version-gates.js";

// Main serializer/deserializer
export { AgentSpecSerializer } from "./serializer.js";
export { AgentSpecDeserializer } from "./deserializer.js";
