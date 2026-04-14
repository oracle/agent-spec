import { describe, it, expect } from "vitest";
import {
  createStdioTransport,
  createSSETransport,
  createSSEmTLSTransport,
  createStreamableHTTPTransport,
  createStreamableHTTPmTLSTransport,
  createRemoteTransport,
} from "../../src/index.js";

describe("StdioTransport", () => {
  it("should create with required fields", () => {
    const t = createStdioTransport({ name: "stdio", command: "python" });
    expect(t.componentType).toBe("StdioTransport");
    expect(t.command).toBe("python");
    expect(t.args).toEqual([]);
  });

  it("should accept optional fields", () => {
    const t = createStdioTransport({
      name: "stdio",
      command: "python",
      args: ["-m", "server"],
      env: { PYTHONPATH: "/usr/lib" },
      cwd: "/tmp",
    });
    expect(t.args).toEqual(["-m", "server"]);
    expect(t.env).toEqual({ PYTHONPATH: "/usr/lib" });
    expect(t.cwd).toBe("/tmp");
  });

  it("should be frozen", () => {
    const t = createStdioTransport({ name: "stdio", command: "node" });
    expect(Object.isFrozen(t)).toBe(true);
  });
});

describe("SSETransport", () => {
  it("should create with required fields", () => {
    const t = createSSETransport({ name: "sse", url: "http://localhost/sse" });
    expect(t.componentType).toBe("SSETransport");
    expect(t.url).toBe("http://localhost/sse");
  });

  it("should accept headers", () => {
    const t = createSSETransport({
      name: "sse",
      url: "http://localhost/sse",
      headers: { Authorization: "Bearer token" },
      sensitiveHeaders: { "X-Secret": "value" },
    });
    expect(t.headers).toEqual({ Authorization: "Bearer token" });
    expect(t.sensitiveHeaders).toEqual({ "X-Secret": "value" });
  });
});

describe("SSEmTLSTransport", () => {
  it("should create with required fields", () => {
    const t = createSSEmTLSTransport({
      name: "sse-mtls",
      url: "https://localhost/sse",
      keyFile: "/key.pem",
      certFile: "/cert.pem",
      caFile: "/ca.pem",
    });
    expect(t.componentType).toBe("SSEmTLSTransport");
    expect(t.keyFile).toBe("/key.pem");
  });
});

describe("StreamableHTTPTransport", () => {
  it("should create with required fields", () => {
    const t = createStreamableHTTPTransport({
      name: "http",
      url: "http://localhost:8080",
    });
    expect(t.componentType).toBe("StreamableHTTPTransport");
  });
});

describe("StreamableHTTPmTLSTransport", () => {
  it("should create with required fields", () => {
    const t = createStreamableHTTPmTLSTransport({
      name: "http-mtls",
      url: "https://localhost:8080",
      keyFile: "/key.pem",
      certFile: "/cert.pem",
      caFile: "/ca.pem",
    });
    expect(t.componentType).toBe("StreamableHTTPmTLSTransport");
    expect(t.certFile).toBe("/cert.pem");
  });
});

describe("RemoteTransport", () => {
  it("should create with required fields", () => {
    const t = createRemoteTransport({
      name: "remote",
      url: "http://remote-server:9090",
    });
    expect(t.componentType).toBe("RemoteTransport");
    expect(t.url).toBe("http://remote-server:9090");
  });

  it("should have default session parameters", () => {
    const t = createRemoteTransport({
      name: "remote",
      url: "http://localhost",
    });
    expect(t.sessionParameters.readTimeoutSeconds).toBe(60.0);
  });
});
