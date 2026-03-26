import { describe, it, expect } from "vitest";
import {
  createInMemoryCollectionDatastore,
  createOracleDatabaseDatastore,
  createTlsOracleDatabaseConnectionConfig,
  createMTlsOracleDatabaseConnectionConfig,
  createPostgresDatabaseDatastore,
  createTlsPostgresDatabaseConnectionConfig,
} from "../../src/index.js";

describe("InMemoryCollectionDatastore", () => {
  it("should create with required fields", () => {
    const ds = createInMemoryCollectionDatastore({
      name: "in-mem",
      datastoreSchema: { users: { name: { type: "string" } } },
    });
    expect(ds.componentType).toBe("InMemoryCollectionDatastore");
    expect(ds.datastoreSchema).toHaveProperty("users");
  });

  it("should be frozen", () => {
    const ds = createInMemoryCollectionDatastore({
      name: "in-mem",
      datastoreSchema: {},
    });
    expect(Object.isFrozen(ds)).toBe(true);
  });
});

describe("TlsOracleDatabaseConnectionConfig", () => {
  it("should create with required fields", () => {
    const config = createTlsOracleDatabaseConnectionConfig({
      name: "oracle-conn",
      user: "admin",
      password: "secret",
      dsn: "localhost:1521/orcl",
    });
    expect(config.componentType).toBe("TlsOracleDatabaseConnectionConfig");
    expect(config.protocol).toBe("tcps");
  });

  it("should accept optional fields", () => {
    const config = createTlsOracleDatabaseConnectionConfig({
      name: "oracle-conn",
      user: "admin",
      password: "secret",
      dsn: "localhost:1521/orcl",
      configDir: "/etc/oracle",
      protocol: "tcp",
    });
    expect(config.configDir).toBe("/etc/oracle");
    expect(config.protocol).toBe("tcp");
  });
});

describe("MTlsOracleDatabaseConnectionConfig", () => {
  it("should create with required fields", () => {
    const config = createMTlsOracleDatabaseConnectionConfig({
      name: "oracle-mtls-conn",
      user: "admin",
      password: "secret",
      dsn: "localhost:1521/orcl",
      walletLocation: "/etc/wallet",
      walletPassword: "wallet-pass",
    });
    expect(config.componentType).toBe("MTlsOracleDatabaseConnectionConfig");
    expect(config.walletLocation).toBe("/etc/wallet");
  });
});

describe("OracleDatabaseDatastore", () => {
  it("should create with TLS connection config", () => {
    const config = createTlsOracleDatabaseConnectionConfig({
      name: "conn",
      user: "admin",
      password: "secret",
      dsn: "localhost:1521/orcl",
    });
    const ds = createOracleDatabaseDatastore({
      name: "oracle-ds",
      datastoreSchema: { table1: { col1: { type: "string" } } },
      connectionConfig: config,
    });
    expect(ds.componentType).toBe("OracleDatabaseDatastore");
    expect(ds.connectionConfig.componentType).toBe(
      "TlsOracleDatabaseConnectionConfig",
    );
  });

  it("should create with mTLS connection config", () => {
    const config = createMTlsOracleDatabaseConnectionConfig({
      name: "conn",
      user: "admin",
      password: "secret",
      dsn: "localhost:1521/orcl",
      walletLocation: "/wallet",
      walletPassword: "pass",
    });
    const ds = createOracleDatabaseDatastore({
      name: "oracle-ds",
      datastoreSchema: {},
      connectionConfig: config,
    });
    expect(ds.connectionConfig.componentType).toBe(
      "MTlsOracleDatabaseConnectionConfig",
    );
  });
});

describe("TlsPostgresDatabaseConnectionConfig", () => {
  it("should create with required fields", () => {
    const config = createTlsPostgresDatabaseConnectionConfig({
      name: "pg-conn",
      user: "postgres",
      password: "secret",
      url: "postgresql://localhost:5432/db",
    });
    expect(config.componentType).toBe("TlsPostgresDatabaseConnectionConfig");
    expect(config.sslmode).toBe("require");
  });

  it("should accept SSL options", () => {
    const config = createTlsPostgresDatabaseConnectionConfig({
      name: "pg-conn",
      user: "postgres",
      password: "secret",
      url: "postgresql://localhost:5432/db",
      sslmode: "verify-full",
      sslcert: "/cert.pem",
      sslkey: "/key.pem",
      sslrootcert: "/ca.pem",
    });
    expect(config.sslmode).toBe("verify-full");
    expect(config.sslcert).toBe("/cert.pem");
  });
});

describe("PostgresDatabaseDatastore", () => {
  it("should create with connection config", () => {
    const config = createTlsPostgresDatabaseConnectionConfig({
      name: "conn",
      user: "postgres",
      password: "secret",
      url: "postgresql://localhost:5432/db",
    });
    const ds = createPostgresDatabaseDatastore({
      name: "pg-ds",
      datastoreSchema: { users: { id: { type: "integer" } } },
      connectionConfig: config,
    });
    expect(ds.componentType).toBe("PostgresDatabaseDatastore");
    expect(ds.connectionConfig.componentType).toBe(
      "TlsPostgresDatabaseConnectionConfig",
    );
  });

  it("should be frozen", () => {
    const config = createTlsPostgresDatabaseConnectionConfig({
      name: "conn",
      user: "postgres",
      password: "secret",
      url: "postgresql://localhost:5432/db",
    });
    const ds = createPostgresDatabaseDatastore({
      name: "pg-ds",
      datastoreSchema: {},
      connectionConfig: config,
    });
    expect(Object.isFrozen(ds)).toBe(true);
  });
});
