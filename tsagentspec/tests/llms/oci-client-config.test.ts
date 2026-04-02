import { describe, it, expect } from "vitest";
import {
  createOciClientConfigWithApiKey,
  createOciClientConfigWithInstancePrincipal,
  createOciClientConfigWithResourcePrincipal,
  createOciClientConfigWithSecurityToken,
} from "../../src/index.js";

describe("OciClientConfigWithApiKey", () => {
  it("should create with required fields", () => {
    const config = createOciClientConfigWithApiKey({
      name: "oci-api-key",
      serviceEndpoint: "https://genai.us-chicago-1.oci.oraclecloud.com",
      authProfile: "DEFAULT",
      authFileLocation: "~/.oci/config",
    });
    expect(config.componentType).toBe("OciClientConfigWithApiKey");
    expect(config.serviceEndpoint).toBe(
      "https://genai.us-chicago-1.oci.oraclecloud.com",
    );
    expect(config.authProfile).toBe("DEFAULT");
    expect(config.authFileLocation).toBe("~/.oci/config");
    expect(config.authType).toBe("API_KEY");
  });

  it("should accept optional fields", () => {
    const config = createOciClientConfigWithApiKey({
      name: "oci-api-key",
      serviceEndpoint: "https://genai.oci.oraclecloud.com",
      authProfile: "PROD",
      authFileLocation: "/etc/oci/config",
      description: "Production OCI config",
      metadata: { env: "prod" },
    });
    expect(config.description).toBe("Production OCI config");
    expect(config.metadata).toEqual({ env: "prod" });
  });

  it("should be frozen", () => {
    const config = createOciClientConfigWithApiKey({
      name: "c",
      serviceEndpoint: "https://x",
      authProfile: "p",
      authFileLocation: "f",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });
});

describe("OciClientConfigWithInstancePrincipal", () => {
  it("should create with required fields", () => {
    const config = createOciClientConfigWithInstancePrincipal({
      name: "oci-instance",
      serviceEndpoint: "https://genai.oci.oraclecloud.com",
    });
    expect(config.componentType).toBe("OciClientConfigWithInstancePrincipal");
    expect(config.authType).toBe("INSTANCE_PRINCIPAL");
    expect(config.serviceEndpoint).toBe("https://genai.oci.oraclecloud.com");
  });

  it("should be frozen", () => {
    const config = createOciClientConfigWithInstancePrincipal({
      name: "c",
      serviceEndpoint: "https://x",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });
});

describe("OciClientConfigWithResourcePrincipal", () => {
  it("should create with required fields", () => {
    const config = createOciClientConfigWithResourcePrincipal({
      name: "oci-resource",
      serviceEndpoint: "https://genai.oci.oraclecloud.com",
    });
    expect(config.componentType).toBe("OciClientConfigWithResourcePrincipal");
    expect(config.authType).toBe("RESOURCE_PRINCIPAL");
    expect(config.serviceEndpoint).toBe("https://genai.oci.oraclecloud.com");
  });

  it("should be frozen", () => {
    const config = createOciClientConfigWithResourcePrincipal({
      name: "c",
      serviceEndpoint: "https://x",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });
});

describe("OciClientConfigWithSecurityToken", () => {
  it("should create with required fields", () => {
    const config = createOciClientConfigWithSecurityToken({
      name: "oci-sec-token",
      serviceEndpoint: "https://genai.oci.oraclecloud.com",
      authProfile: "TOKEN_PROFILE",
      authFileLocation: "~/.oci/sessions/token",
    });
    expect(config.componentType).toBe("OciClientConfigWithSecurityToken");
    expect(config.authType).toBe("SECURITY_TOKEN");
    expect(config.authProfile).toBe("TOKEN_PROFILE");
    expect(config.authFileLocation).toBe("~/.oci/sessions/token");
  });

  it("should accept optional fields", () => {
    const config = createOciClientConfigWithSecurityToken({
      name: "oci-sec-token",
      serviceEndpoint: "https://genai.oci.oraclecloud.com",
      authProfile: "PROFILE",
      authFileLocation: "/path/to/config",
      description: "Security token config",
      metadata: { region: "us-chicago-1" },
    });
    expect(config.description).toBe("Security token config");
    expect(config.metadata).toEqual({ region: "us-chicago-1" });
  });

  it("should be frozen", () => {
    const config = createOciClientConfigWithSecurityToken({
      name: "c",
      serviceEndpoint: "https://x",
      authProfile: "p",
      authFileLocation: "f",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });
});
