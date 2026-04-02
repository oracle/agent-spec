/**
 * Datastore types.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

export const InMemoryCollectionDatastoreSchema = ComponentBaseSchema.extend({
  componentType: z.literal("InMemoryCollectionDatastore"),
  datastoreSchema: z.record(z.record(z.unknown())),
});

export type InMemoryCollectionDatastore = z.infer<
  typeof InMemoryCollectionDatastoreSchema
>;

export function createInMemoryCollectionDatastore(opts: {
  name: string;
  datastoreSchema: Record<string, Record<string, unknown>>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): InMemoryCollectionDatastore {
  return Object.freeze(
    InMemoryCollectionDatastoreSchema.parse({
      ...opts,
      componentType: "InMemoryCollectionDatastore" as const,
    }),
  );
}
