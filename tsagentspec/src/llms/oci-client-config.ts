/**
 * OCI client config types for connecting to OCI GenAI.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

export const OciClientConfigWithApiKeySchema = ComponentBaseSchema.extend({
  componentType: z.literal("OciClientConfigWithApiKey"),
  serviceEndpoint: z.string(),
  authType: z.literal("API_KEY").default("API_KEY"),
  authProfile: z.string(),
  authFileLocation: z.string(),
});

export type OciClientConfigWithApiKey = z.infer<
  typeof OciClientConfigWithApiKeySchema
>;

export const OciClientConfigWithInstancePrincipalSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("OciClientConfigWithInstancePrincipal"),
    serviceEndpoint: z.string(),
    authType: z.literal("INSTANCE_PRINCIPAL").default("INSTANCE_PRINCIPAL"),
  });

export type OciClientConfigWithInstancePrincipal = z.infer<
  typeof OciClientConfigWithInstancePrincipalSchema
>;

export const OciClientConfigWithResourcePrincipalSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("OciClientConfigWithResourcePrincipal"),
    serviceEndpoint: z.string(),
    authType: z.literal("RESOURCE_PRINCIPAL").default("RESOURCE_PRINCIPAL"),
  });

export type OciClientConfigWithResourcePrincipal = z.infer<
  typeof OciClientConfigWithResourcePrincipalSchema
>;

export const OciClientConfigWithSecurityTokenSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("OciClientConfigWithSecurityToken"),
    serviceEndpoint: z.string(),
    authType: z.literal("SECURITY_TOKEN").default("SECURITY_TOKEN"),
    authProfile: z.string(),
    authFileLocation: z.string(),
  });

export type OciClientConfigWithSecurityToken = z.infer<
  typeof OciClientConfigWithSecurityTokenSchema
>;

export const OciClientConfigUnion = z.discriminatedUnion("componentType", [
  OciClientConfigWithApiKeySchema,
  OciClientConfigWithInstancePrincipalSchema,
  OciClientConfigWithResourcePrincipalSchema,
  OciClientConfigWithSecurityTokenSchema,
]);

export type OciClientConfig = z.infer<typeof OciClientConfigUnion>;

export function createOciClientConfigWithApiKey(opts: {
  name: string;
  serviceEndpoint: string;
  authProfile: string;
  authFileLocation: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): OciClientConfigWithApiKey {
  return Object.freeze(
    OciClientConfigWithApiKeySchema.parse({
      ...opts,
      componentType: "OciClientConfigWithApiKey" as const,
    }),
  );
}

export function createOciClientConfigWithInstancePrincipal(opts: {
  name: string;
  serviceEndpoint: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): OciClientConfigWithInstancePrincipal {
  return Object.freeze(
    OciClientConfigWithInstancePrincipalSchema.parse({
      ...opts,
      componentType: "OciClientConfigWithInstancePrincipal" as const,
    }),
  );
}

export function createOciClientConfigWithResourcePrincipal(opts: {
  name: string;
  serviceEndpoint: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): OciClientConfigWithResourcePrincipal {
  return Object.freeze(
    OciClientConfigWithResourcePrincipalSchema.parse({
      ...opts,
      componentType: "OciClientConfigWithResourcePrincipal" as const,
    }),
  );
}

export function createOciClientConfigWithSecurityToken(opts: {
  name: string;
  serviceEndpoint: string;
  authProfile: string;
  authFileLocation: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): OciClientConfigWithSecurityToken {
  return Object.freeze(
    OciClientConfigWithSecurityTokenSchema.parse({
      ...opts,
      componentType: "OciClientConfigWithSecurityToken" as const,
    }),
  );
}
