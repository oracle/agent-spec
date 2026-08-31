/**
 * ManagerWorkers multi-agent component.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import { propertiesHaveSameType, type Property } from "../property.js";

// z.record(z.unknown()) is used instead of AgenticComponentUnion to break a circular
// dependency (ManagerWorkers -> AgenticComponentUnion -> ManagerWorkers). Validation of
// the nested agents is handled by the deserialization plugin at runtime.
const AgenticComponentRef = z.lazy(() => z.record(z.unknown()));

export const ManagerWorkersSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("ManagerWorkers"),
  groupManager: AgenticComponentRef,
  workers: z.array(AgenticComponentRef).min(1, "Cannot define a ManagerWorkers with no worker. Use an Agent instead."),
});

export type ManagerWorkers = z.infer<typeof ManagerWorkersSchema>;

function getComponentProperties(
  component: Record<string, unknown>,
  field: "inputs" | "outputs",
): Property[] {
  const properties = component[field];
  return Array.isArray(properties) ? (properties as Property[]) : [];
}

function validatePropertiesMatchManager(
  properties: Property[],
  managerProperties: Property[],
  kind: "inputs" | "outputs",
): void {
  const managerPropertiesByTitle = new Map(
    managerProperties.map((property) => [property.title, property]),
  );
  const propertiesByTitle = new Map(
    properties.map((property) => [property.title, property]),
  );
  if (
    propertiesByTitle.size !== properties.length ||
    propertiesByTitle.size !== managerPropertiesByTitle.size
  ) {
    throw new Error(
      `The ${kind} of a ManagerWorkers must match the ${kind} of its group manager.`,
    );
  }
  for (const property of properties) {
    const managerProperty = managerPropertiesByTitle.get(property.title);
    if (!managerProperty || !propertiesHaveSameType(property, managerProperty)) {
      throw new Error(
        `The ${kind} of a ManagerWorkers must match the ${kind} of its group manager.`,
      );
    }
  }
}

export function createManagerWorkers(opts: {
  name: string;
  groupManager: Record<string, unknown>;
  workers: Record<string, unknown>[];
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): ManagerWorkers {
  if (opts.workers.some(w => w === opts.groupManager)) {
    throw new Error("Group manager cannot be a worker.");
  }
  const managerInputs = getComponentProperties(opts.groupManager, "inputs");
  const managerOutputs = getComponentProperties(opts.groupManager, "outputs");
  if (opts.inputs !== undefined) {
    validatePropertiesMatchManager(opts.inputs, managerInputs, "inputs");
  }
  if (opts.outputs !== undefined) {
    validatePropertiesMatchManager(opts.outputs, managerOutputs, "outputs");
  }
  return Object.freeze(
    ManagerWorkersSchema.parse({
      ...opts,
      inputs: opts.inputs ?? managerInputs,
      outputs: opts.outputs ?? managerOutputs,
      componentType: "ManagerWorkers" as const,
    }),
  );
}
