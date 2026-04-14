/**
 * PostgreSQL datastore and connection config.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

export const TlsPostgresDatabaseConnectionConfigSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("TlsPostgresDatabaseConnectionConfig"),
    user: z.string(),
    password: z.string(),
    url: z.string(),
    sslmode: z
      .enum([
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
      ])
      .default("require"),
    sslcert: z.string().optional(),
    sslkey: z.string().optional(),
    sslrootcert: z.string().optional(),
    sslcrl: z.string().optional(),
  });

export type TlsPostgresDatabaseConnectionConfig = z.infer<
  typeof TlsPostgresDatabaseConnectionConfigSchema
>;

export const PostgresDatabaseDatastoreSchema = ComponentBaseSchema.extend({
  componentType: z.literal("PostgresDatabaseDatastore"),
  datastoreSchema: z.record(z.record(z.unknown())),
  connectionConfig: TlsPostgresDatabaseConnectionConfigSchema,
});

export type PostgresDatabaseDatastore = z.infer<
  typeof PostgresDatabaseDatastoreSchema
>;

export function createTlsPostgresDatabaseConnectionConfig(opts: {
  name: string;
  user: string;
  password: string;
  url: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  sslmode?: "disable" | "allow" | "prefer" | "require" | "verify-ca" | "verify-full";
  sslcert?: string;
  sslkey?: string;
  sslrootcert?: string;
  sslcrl?: string;
}): TlsPostgresDatabaseConnectionConfig {
  return Object.freeze(
    TlsPostgresDatabaseConnectionConfigSchema.parse({
      ...opts,
      componentType: "TlsPostgresDatabaseConnectionConfig" as const,
    }),
  );
}

export function createPostgresDatabaseDatastore(opts: {
  name: string;
  datastoreSchema: Record<string, Record<string, unknown>>;
  connectionConfig: TlsPostgresDatabaseConnectionConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): PostgresDatabaseDatastore {
  return Object.freeze(
    PostgresDatabaseDatastoreSchema.parse({
      ...opts,
      componentType: "PostgresDatabaseDatastore" as const,
    }),
  );
}
