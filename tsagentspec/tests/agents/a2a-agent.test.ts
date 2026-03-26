import { describe, it, expect } from "vitest";
import {
  createA2AAgent,
  createA2AConnectionConfig,
} from "../../src/index.js";

describe("A2AConnectionConfig", () => {
  it("should create with required fields", () => {
    const config = createA2AConnectionConfig({ name: "a2a-conn" });
    expect(config.componentType).toBe("A2AConnectionConfig");
    expect(config.name).toBe("a2a-conn");
    expect(config.timeout).toBe(600.0);
    expect(config.verify).toBe(true);
  });

  it("should accept optional fields", () => {
    const config = createA2AConnectionConfig({
      name: "a2a-conn",
      timeout: 300,
      headers: { "X-Custom": "value" },
      verify: false,
      keyFile: "/path/to/key",
      certFile: "/path/to/cert",
      sslCaCert: "/path/to/ca",
    });
    expect(config.timeout).toBe(300);
    expect(config.headers).toEqual({ "X-Custom": "value" });
    expect(config.verify).toBe(false);
  });

  it("should be frozen", () => {
    const config = createA2AConnectionConfig({ name: "c" });
    expect(Object.isFrozen(config)).toBe(true);
  });
});

describe("A2AAgent", () => {
  it("should create with required fields", () => {
    const config = createA2AConnectionConfig({ name: "conn" });
    const agent = createA2AAgent({
      name: "a2a-agent",
      agentUrl: "https://example.com/agent",
      connectionConfig: config,
    });
    expect(agent.componentType).toBe("A2AAgent");
    expect(agent.agentUrl).toBe("https://example.com/agent");
    expect(agent.connectionConfig.componentType).toBe("A2AConnectionConfig");
  });

  it("should have default session parameters", () => {
    const config = createA2AConnectionConfig({ name: "conn" });
    const agent = createA2AAgent({
      name: "a2a-agent",
      agentUrl: "https://example.com/agent",
      connectionConfig: config,
    });
    expect(agent.sessionParameters.timeout).toBe(60.0);
    expect(agent.sessionParameters.pollInterval).toBe(2.0);
    expect(agent.sessionParameters.maxRetries).toBe(5);
  });

  it("should be frozen", () => {
    const config = createA2AConnectionConfig({ name: "conn" });
    const agent = createA2AAgent({
      name: "a2a-agent",
      agentUrl: "https://example.com/agent",
      connectionConfig: config,
    });
    expect(Object.isFrozen(agent)).toBe(true);
  });
});
