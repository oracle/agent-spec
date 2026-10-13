import { describe, expect, it } from "vitest";
import {
  createInMemoryCollectionDatastore,
  createOracleDatabaseDatastore,
  createPostgresDatabaseDatastore,
  createTlsOracleDatabaseConnectionConfig,
  createTlsPostgresDatabaseConnectionConfig,
} from "../../../src/index.js";
import {
  resolveMastraDatastore,
  UnsupportedMastraDatastoreError,
} from "../../../src/adapters/mastra/index.js";

describe("Mastra datastore resolver", () => {
  it("maps InMemoryCollectionDatastore to Mastra InMemoryStore target", () => {
    const datastore = createInMemoryCollectionDatastore({
      id: "memory-ds",
      name: "memory",
      datastoreSchema: { cache: { value: { type: "string" } } },
    });

    const target = resolveMastraDatastore(datastore);

    expect(target).toMatchObject({
      provider: "in-memory",
      packageName: "@mastra/core/storage",
      exportName: "InMemoryStore",
      id: "memory-ds",
      config: { id: "memory-ds" },
    });
    expect(target.datastoreSchema).toEqual(datastore.datastoreSchema);
  });

  it("maps PostgresDatabaseDatastore url to PostgresStore connectionString", () => {
    const datastore = createPostgresDatabaseDatastore({
      id: "pg-ds",
      name: "postgres",
      datastoreSchema: { users: { id: { type: "string" } } },
      connectionConfig: createTlsPostgresDatabaseConnectionConfig({
        name: "pg-connection",
        user: "postgres",
        password: "secret",
        url: "postgresql://localhost:5432/agentspec",
        sslmode: "verify-full",
        sslcert: "/certs/client.pem",
        sslkey: "/certs/client-key.pem",
        sslrootcert: "/certs/ca.pem",
        sslcrl: "/certs/crl.pem",
      }),
    });

    const target = resolveMastraDatastore(datastore, {
      schemaName: "agentspec",
      disableInit: true,
    });

    expect(target.provider).toBe("postgres");
    expect(target.packageName).toBe("@mastra/pg");
    expect(target.exportName).toBe("PostgresStore");
    expect(target.config).toEqual({
      id: "pg-ds",
      connectionString: "postgresql://localhost:5432/agentspec",
      user: "postgres",
      password: "secret",
      ssl: {
        mode: "verify-full",
        certPath: "/certs/client.pem",
        keyPath: "/certs/client-key.pem",
        rootCertPath: "/certs/ca.pem",
        crlPath: "/certs/crl.pem",
      },
      schemaName: "agentspec",
      disableInit: true,
    });
  });

  it("maps disabled Postgres SSL mode to false", () => {
    const datastore = createPostgresDatabaseDatastore({
      id: "pg-no-ssl",
      name: "postgres",
      datastoreSchema: {},
      connectionConfig: createTlsPostgresDatabaseConnectionConfig({
        name: "pg-connection",
        user: "postgres",
        password: "secret",
        url: "postgresql://localhost:5432/agentspec",
        sslmode: "disable",
      }),
    });

    const target = resolveMastraDatastore(datastore);

    expect(target.provider).toBe("postgres");
    expect(target.config.ssl).toBe(false);
  });

  it("does not map OracleDatabaseDatastore until Mastra publishes an official provider", () => {
    const datastore = createOracleDatabaseDatastore({
      id: "oracle-ds",
      name: "oracle",
      datastoreSchema: { threads: { id: { type: "string" } } },
      connectionConfig: createTlsOracleDatabaseConnectionConfig({
        name: "oracle-connection",
        user: "admin",
        password: "secret",
        dsn: "localhost:1521/FREEPDB1",
        configDir: "/opt/oracle/network/admin",
      }),
    });

    expect(() => resolveMastraDatastore(datastore)).toThrow(
      UnsupportedMastraDatastoreError,
    );
  });
});
