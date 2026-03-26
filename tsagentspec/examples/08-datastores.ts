/**
 * Example 8: Datastores
 *
 * Demonstrates configuring in-memory, Oracle Database, and PostgreSQL
 * datastores for agent data persistence.
 */
import {
  createInMemoryCollectionDatastore,
  createOracleDatabaseDatastore,
  createTlsOracleDatabaseConnectionConfig,
  createMTlsOracleDatabaseConnectionConfig,
  createPostgresDatabaseDatastore,
  createTlsPostgresDatabaseConnectionConfig,
  AgentSpecSerializer,
} from "agentspec";

// =============================================
// In-memory datastore
// =============================================

// datastoreSchema defines the shape of records using JSON Schema.
const memoryStore = createInMemoryCollectionDatastore({
  name: "session-cache",
  description: "Ephemeral in-memory storage for session data",
  datastoreSchema: {
    id: { type: "string" },
    content: { type: "string" },
    role: { type: "string", enum: ["system", "user", "assistant"] },
  },
});

console.log("In-memory store:", memoryStore.name);
console.log("Schema fields:", Object.keys(memoryStore.datastoreSchema));

// =============================================
// Oracle Database datastore (TLS)
// =============================================

// Connection credentials (user, password, dsn) live on the connection config.
// These are excluded from serialization for security.
const oracleTlsConfig = createTlsOracleDatabaseConnectionConfig({
  name: "oracle-tls-conn",
  user: "agent_user",
  password: "db-secret",
  dsn: "mydb_high",
  protocol: "tcps",
});

const oracleStore = createOracleDatabaseDatastore({
  name: "oracle-knowledge-base",
  description: "Oracle DB-backed knowledge store",
  datastoreSchema: {
    doc_id: { type: "string" },
    embedding: { type: "array", items: { type: "number" } },
    text: { type: "string" },
  },
  connectionConfig: oracleTlsConfig,
});

console.log("\nOracle store:", oracleStore.name);

// =============================================
// Oracle Database datastore (mTLS with wallet)
// =============================================

const oracleMtlsConfig = createMTlsOracleDatabaseConnectionConfig({
  name: "oracle-mtls-conn",
  user: "secure_user",
  password: "secure-secret",
  dsn: "mydb_tls",
  walletLocation: "/opt/oracle/wallet",
  walletPassword: "wallet-secret",
});

const oracleSecureStore = createOracleDatabaseDatastore({
  name: "oracle-secure-store",
  description: "Oracle DB with mutual TLS",
  datastoreSchema: {
    record_id: { type: "string" },
    data: { type: "object" },
  },
  connectionConfig: oracleMtlsConfig,
});

console.log("Oracle mTLS store:", oracleSecureStore.name);

// =============================================
// PostgreSQL datastore
// =============================================

const pgTlsConfig = createTlsPostgresDatabaseConnectionConfig({
  name: "pg-tls-conn",
  user: "vector_user",
  password: "pg-secret",
  url: "postgresql://localhost:5432/vectors",
  sslmode: "verify-full",
  sslrootcert: "/etc/ssl/certs/pg-ca.pem",
});

const pgStore = createPostgresDatabaseDatastore({
  name: "pg-vector-store",
  description: "PostgreSQL vector store for embeddings",
  datastoreSchema: {
    id: { type: "integer" },
    embedding: { type: "array", items: { type: "number" } },
    metadata: { type: "object" },
  },
  connectionConfig: pgTlsConfig,
});

console.log("PostgreSQL store:", pgStore.name);

// --- Serialize (sensitive fields like user, password, dsn are excluded) ---

const serializer = new AgentSpecSerializer();
console.log("\n--- Oracle datastore (YAML) ---");
console.log(serializer.toYaml(oracleStore));
console.log("Note: user, password, dsn, and wallet credentials are excluded.");
