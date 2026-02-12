/**
 * MCP client transport types.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

const SessionParametersSchema = z.object({
  readTimeoutSeconds: z.number().default(60.0),
});

const ClientTransportBaseSchema = ComponentBaseSchema.extend({
  sessionParameters: SessionParametersSchema.default({}),
});

export const StdioTransportSchema = ClientTransportBaseSchema.extend({
  componentType: z.literal("StdioTransport"),
  command: z.string(),
  args: z.array(z.string()).default([]),
  env: z.record(z.string()).optional(),
  cwd: z.string().optional(),
});

export type StdioTransport = z.infer<typeof StdioTransportSchema>;

const RemoteTransportBaseSchema = ClientTransportBaseSchema.extend({
  url: z.string(),
  headers: z.record(z.string()).optional(),
  sensitiveHeaders: z.record(z.string()).optional(),
});

export const SSETransportSchema = RemoteTransportBaseSchema.extend({
  componentType: z.literal("SSETransport"),
});

export type SSETransport = z.infer<typeof SSETransportSchema>;

export const SSEmTLSTransportSchema = RemoteTransportBaseSchema.extend({
  componentType: z.literal("SSEmTLSTransport"),
  keyFile: z.string(),
  certFile: z.string(),
  caFile: z.string(),
});

export type SSEmTLSTransport = z.infer<typeof SSEmTLSTransportSchema>;

export const StreamableHTTPTransportSchema = RemoteTransportBaseSchema.extend({
  componentType: z.literal("StreamableHTTPTransport"),
});

export type StreamableHTTPTransport = z.infer<
  typeof StreamableHTTPTransportSchema
>;

export const StreamableHTTPmTLSTransportSchema =
  RemoteTransportBaseSchema.extend({
    componentType: z.literal("StreamableHTTPmTLSTransport"),
    keyFile: z.string(),
    certFile: z.string(),
    caFile: z.string(),
  });

export type StreamableHTTPmTLSTransport = z.infer<
  typeof StreamableHTTPmTLSTransportSchema
>;

export const RemoteTransportSchema = RemoteTransportBaseSchema.extend({
  componentType: z.literal("RemoteTransport"),
});

export type RemoteTransport = z.infer<typeof RemoteTransportSchema>;

export const ClientTransportUnion = z.discriminatedUnion("componentType", [
  StdioTransportSchema,
  SSETransportSchema,
  SSEmTLSTransportSchema,
  StreamableHTTPTransportSchema,
  StreamableHTTPmTLSTransportSchema,
  RemoteTransportSchema,
]);

export type ClientTransport = z.infer<typeof ClientTransportUnion>;

export function createStdioTransport(opts: {
  name: string;
  command: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  sessionParameters?: { readTimeoutSeconds?: number };
}): StdioTransport {
  return Object.freeze(
    StdioTransportSchema.parse({
      ...opts,
      componentType: "StdioTransport" as const,
    }),
  );
}

export function createSSETransport(opts: {
  name: string;
  url: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  headers?: Record<string, string>;
  sensitiveHeaders?: Record<string, string>;
  sessionParameters?: { readTimeoutSeconds?: number };
}): SSETransport {
  return Object.freeze(
    SSETransportSchema.parse({
      ...opts,
      componentType: "SSETransport" as const,
    }),
  );
}

export function createSSEmTLSTransport(opts: {
  name: string;
  url: string;
  keyFile: string;
  certFile: string;
  caFile: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  headers?: Record<string, string>;
  sensitiveHeaders?: Record<string, string>;
  sessionParameters?: { readTimeoutSeconds?: number };
}): SSEmTLSTransport {
  return Object.freeze(
    SSEmTLSTransportSchema.parse({
      ...opts,
      componentType: "SSEmTLSTransport" as const,
    }),
  );
}

export function createStreamableHTTPTransport(opts: {
  name: string;
  url: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  headers?: Record<string, string>;
  sensitiveHeaders?: Record<string, string>;
  sessionParameters?: { readTimeoutSeconds?: number };
}): StreamableHTTPTransport {
  return Object.freeze(
    StreamableHTTPTransportSchema.parse({
      ...opts,
      componentType: "StreamableHTTPTransport" as const,
    }),
  );
}

export function createStreamableHTTPmTLSTransport(opts: {
  name: string;
  url: string;
  keyFile: string;
  certFile: string;
  caFile: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  headers?: Record<string, string>;
  sensitiveHeaders?: Record<string, string>;
  sessionParameters?: { readTimeoutSeconds?: number };
}): StreamableHTTPmTLSTransport {
  return Object.freeze(
    StreamableHTTPmTLSTransportSchema.parse({
      ...opts,
      componentType: "StreamableHTTPmTLSTransport" as const,
    }),
  );
}

export function createRemoteTransport(opts: {
  name: string;
  url: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  headers?: Record<string, string>;
  sensitiveHeaders?: Record<string, string>;
  sessionParameters?: { readTimeoutSeconds?: number };
}): RemoteTransport {
  return Object.freeze(
    RemoteTransportSchema.parse({
      ...opts,
      componentType: "RemoteTransport" as const,
    }),
  );
}
