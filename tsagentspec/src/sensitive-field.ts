/**
 * Sensitive field tracking for serialization exclusion.
 */
import type { ComponentTypeName } from "./component.js";

export const SENSITIVE_FIELD_MARKER = "SENSITIVE_FIELD_MARKER" as const;

/** Maps componentType -> set of field names that are sensitive */
export const SENSITIVE_FIELDS = {
  LlmConfig: new Set(["apiKey"]),
  GeminiAIStudioAuthConfig: new Set(["apiKey"]),
  GeminiVertexAIAuthConfig: new Set(["credentials"]),
  OpenAiCompatibleConfig: new Set(["apiKey", "keyFile", "certFile", "caFile"]),
  OllamaConfig: new Set(["apiKey", "keyFile", "certFile", "caFile"]),
  VllmConfig: new Set(["apiKey", "keyFile", "certFile", "caFile"]),
  OpenAiConfig: new Set(["apiKey"]),
  RemoteTool: new Set(["sensitiveHeaders"]),
  ApiNode: new Set(["sensitiveHeaders"]),
  SSEmTLSTransport: new Set(["keyFile", "certFile", "caFile"]),
  StreamableHTTPmTLSTransport: new Set(["keyFile", "certFile", "caFile"]),
  RemoteTransport: new Set(["sensitiveHeaders"]),
  SSETransport: new Set(["sensitiveHeaders"]),
  StreamableHTTPTransport: new Set(["sensitiveHeaders"]),
  OciClientConfigWithApiKey: new Set(["authFileLocation"]),
  OciClientConfigWithSecurityToken: new Set(["authFileLocation"]),
  TlsOracleDatabaseConnectionConfig: new Set(["user", "password", "dsn"]),
  MTlsOracleDatabaseConnectionConfig: new Set([
    "user",
    "password",
    "dsn",
    "walletLocation",
    "walletPassword",
  ]),
  TlsPostgresDatabaseConnectionConfig: new Set([
    "user",
    "password",
    "sslkey",
  ]),
} satisfies Partial<Record<ComponentTypeName, Set<string>>>;

/** Check if a field on a component type is sensitive */
export function isSensitiveField(
  componentType: string,
  fieldName: string,
): boolean {
  return (SENSITIVE_FIELDS as Record<string, Set<string> | undefined>)[componentType]?.has(fieldName) ?? false;
}
