import type {
  InMemoryCollectionDatastore,
  OracleDatabaseDatastore,
  PostgresDatabaseDatastore,
  TlsPostgresDatabaseConnectionConfig,
} from "../../datastores/index.js";
import { UnsupportedMastraDatastoreError } from "./errors.js";
import type {
  AgentSpecMastraDatastore,
  MastraDatastoreTarget,
  MastraDatastoreTargetOptions,
  MastraInMemoryDatastoreTarget,
  MastraPostgresDatastoreTarget,
  MastraPostgresSslTarget,
  MastraPostgresStoreConfig,
} from "./types.js";

type MastraDatastoreCandidate =
  | AgentSpecMastraDatastore
  | OracleDatabaseDatastore;

export const resolveMastraDatastore = (
  datastore: MastraDatastoreCandidate,
  options: MastraDatastoreTargetOptions = {},
): MastraDatastoreTarget => {
  if (datastore.componentType === "InMemoryCollectionDatastore") {
    return resolveInMemoryDatastore(datastore, options);
  }

  if (datastore.componentType === "PostgresDatabaseDatastore") {
    return resolvePostgresDatastore(datastore, options);
  }

  throw new UnsupportedMastraDatastoreError(datastore.componentType);
};

export const resolveInMemoryDatastore = (
  datastore: InMemoryCollectionDatastore,
  options: MastraDatastoreTargetOptions = {},
): MastraInMemoryDatastoreTarget => {
  const id = options.id ?? datastore.id;

  return {
    provider: "in-memory",
    packageName: "@mastra/core/storage",
    exportName: "InMemoryStore",
    id,
    datastoreSchema: datastore.datastoreSchema,
    config: { id },
  };
};

export const resolvePostgresDatastore = (
  datastore: PostgresDatabaseDatastore,
  options: MastraDatastoreTargetOptions = {},
): MastraPostgresDatastoreTarget => {
  const id = options.id ?? datastore.id;
  const connection = datastore.connectionConfig;
  // Datastore resolvers only build an import/config target. They should never
  // open sockets, run migrations, or require the Mastra provider package.
  const config: MastraPostgresStoreConfig = {
    id,
    connectionString: connection.url,
    user: connection.user,
    password: connection.password,
    ssl: resolvePostgresSslTarget(connection),
    ...storageRuntimeOptions(options),
  };

  return {
    provider: "postgres",
    packageName: "@mastra/pg",
    exportName: "PostgresStore",
    id,
    datastoreSchema: datastore.datastoreSchema,
    config,
  };
};

const resolvePostgresSslTarget = (
  connection: TlsPostgresDatabaseConnectionConfig,
): MastraPostgresSslTarget => {
  if (connection.sslmode === "disable") {
    return false;
  }

  return {
    mode: connection.sslmode,
    ...(connection.sslcert ? { certPath: connection.sslcert } : {}),
    ...(connection.sslkey ? { keyPath: connection.sslkey } : {}),
    ...(connection.sslrootcert ? { rootCertPath: connection.sslrootcert } : {}),
    ...(connection.sslcrl ? { crlPath: connection.sslcrl } : {}),
  };
};

const storageRuntimeOptions = (
  options: MastraDatastoreTargetOptions,
): Pick<MastraPostgresStoreConfig, "schemaName" | "disableInit"> => ({
  ...(options.schemaName ? { schemaName: options.schemaName } : {}),
  ...(options.disableInit === undefined
    ? {}
    : { disableInit: options.disableInit }),
});
