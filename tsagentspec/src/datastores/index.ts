/**
 * Datastores barrel exports.
 */
export {
  InMemoryCollectionDatastoreSchema,
  createInMemoryCollectionDatastore,
  type InMemoryCollectionDatastore,
} from "./datastore.js";

export {
  OracleDatabaseDatastoreSchema,
  TlsOracleDatabaseConnectionConfigSchema,
  MTlsOracleDatabaseConnectionConfigSchema,
  createOracleDatabaseDatastore,
  createTlsOracleDatabaseConnectionConfig,
  createMTlsOracleDatabaseConnectionConfig,
  type OracleDatabaseDatastore,
  type TlsOracleDatabaseConnectionConfig,
  type MTlsOracleDatabaseConnectionConfig,
} from "./oracle-datastore.js";

export {
  PostgresDatabaseDatastoreSchema,
  TlsPostgresDatabaseConnectionConfigSchema,
  createPostgresDatabaseDatastore,
  createTlsPostgresDatabaseConnectionConfig,
  type PostgresDatabaseDatastore,
  type TlsPostgresDatabaseConnectionConfig,
} from "./postgres-datastore.js";
