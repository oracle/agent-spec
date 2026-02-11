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
