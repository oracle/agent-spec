/**
 * Oracle Database datastore and connection configs.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

export const TlsOracleDatabaseConnectionConfigSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("TlsOracleDatabaseConnectionConfig"),
    user: z.string(),
    password: z.string(),
    dsn: z.string(),
    configDir: z.string().optional(),
    protocol: z.enum(["tcp", "tcps"]).default("tcps"),
  });

export type TlsOracleDatabaseConnectionConfig = z.infer<
  typeof TlsOracleDatabaseConnectionConfigSchema
>;

export const MTlsOracleDatabaseConnectionConfigSchema =
  TlsOracleDatabaseConnectionConfigSchema.extend({
    componentType: z.literal("MTlsOracleDatabaseConnectionConfig"),
    walletLocation: z.string(),
    walletPassword: z.string(),
  });

export type MTlsOracleDatabaseConnectionConfig = z.infer<
  typeof MTlsOracleDatabaseConnectionConfigSchema
>;

const OracleConnectionConfigUnion = z.discriminatedUnion("componentType", [
  TlsOracleDatabaseConnectionConfigSchema,
  MTlsOracleDatabaseConnectionConfigSchema,
]);

export const OracleDatabaseDatastoreSchema = ComponentBaseSchema.extend({
  componentType: z.literal("OracleDatabaseDatastore"),
  datastoreSchema: z.record(z.record(z.unknown())),
  connectionConfig: OracleConnectionConfigUnion,
});

export type OracleDatabaseDatastore = z.infer<
  typeof OracleDatabaseDatastoreSchema
>;

export function createTlsOracleDatabaseConnectionConfig(opts: {
  name: string;
  user: string;
  password: string;
  dsn: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  configDir?: string;
  protocol?: "tcp" | "tcps";
}): TlsOracleDatabaseConnectionConfig {
  return Object.freeze(
    TlsOracleDatabaseConnectionConfigSchema.parse({
      ...opts,
      componentType: "TlsOracleDatabaseConnectionConfig" as const,
    }),
  );
}

export function createMTlsOracleDatabaseConnectionConfig(opts: {
  name: string;
  user: string;
  password: string;
  dsn: string;
  walletLocation: string;
  walletPassword: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  configDir?: string;
  protocol?: "tcp" | "tcps";
}): MTlsOracleDatabaseConnectionConfig {
  return Object.freeze(
    MTlsOracleDatabaseConnectionConfigSchema.parse({
      ...opts,
      componentType: "MTlsOracleDatabaseConnectionConfig" as const,
    }),
  );
}

export function createOracleDatabaseDatastore(opts: {
  name: string;
  datastoreSchema: Record<string, Record<string, unknown>>;
  connectionConfig: TlsOracleDatabaseConnectionConfig | MTlsOracleDatabaseConnectionConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): OracleDatabaseDatastore {
  return Object.freeze(
    OracleDatabaseDatastoreSchema.parse({
      ...opts,
      componentType: "OracleDatabaseDatastore" as const,
    }),
  );
}
