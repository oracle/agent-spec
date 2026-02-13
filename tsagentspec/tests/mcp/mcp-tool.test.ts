import { describe, it, expect } from "vitest";
import {
  createMCPTool,
  createMCPToolSpec,
  createStdioTransport,
  createSSETransport,
  stringProperty,
} from "../../src/index.js";

describe("MCPTool", () => {
  it("should create with stdio transport", () => {
    const transport = createStdioTransport({
      name: "stdio",
      command: "python",
      args: ["-m", "mcp_server"],
    });
    const tool = createMCPTool({
      name: "mcp-tool",
      clientTransport: transport,
    });
    expect(tool.componentType).toBe("MCPTool");
    expect(tool.clientTransport.componentType).toBe("StdioTransport");
  });

  it("should create with SSE transport", () => {
    const transport = createSSETransport({
      name: "sse",
      url: "http://localhost:8080/sse",
    });
    const tool = createMCPTool({
      name: "mcp-tool",
      clientTransport: transport,
    });
    expect(tool.clientTransport.componentType).toBe("SSETransport");
  });

  it("should accept inputs and outputs", () => {
    const transport = createStdioTransport({
      name: "stdio",
      command: "node",
    });
    const tool = createMCPTool({
      name: "mcp-tool",
      clientTransport: transport,
      inputs: [stringProperty({ title: "query" })],
      outputs: [stringProperty({ title: "result" })],
    });
    expect(tool.inputs).toHaveLength(1);
    expect(tool.outputs).toHaveLength(1);
  });

  it("should accept requiresConfirmation", () => {
    const transport = createStdioTransport({
      name: "stdio",
      command: "node",
    });
    const tool = createMCPTool({
      name: "mcp-tool",
      clientTransport: transport,
      requiresConfirmation: true,
    });
    expect(tool.requiresConfirmation).toBe(true);
  });

  it("should be frozen", () => {
    const transport = createStdioTransport({
      name: "stdio",
      command: "node",
    });
    const tool = createMCPTool({
      name: "mcp-tool",
      clientTransport: transport,
    });
    expect(Object.isFrozen(tool)).toBe(true);
  });
});

describe("MCPToolSpec", () => {
  it("should create with required fields", () => {
    const spec = createMCPToolSpec({ name: "tool-spec" });
    expect(spec.componentType).toBe("MCPToolSpec");
    expect(spec.requiresConfirmation).toBe(false);
  });

  it("should accept requiresConfirmation", () => {
    const spec = createMCPToolSpec({
      name: "tool-spec",
      requiresConfirmation: true,
    });
    expect(spec.requiresConfirmation).toBe(true);
  });

  it("should be frozen", () => {
    const spec = createMCPToolSpec({ name: "tool-spec" });
    expect(Object.isFrozen(spec)).toBe(true);
  });
});
