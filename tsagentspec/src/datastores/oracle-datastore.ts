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
