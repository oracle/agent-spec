import { describe, it, expect } from "vitest";
import { createRemoteTool, stringProperty } from "../../src/index.js";

describe("RemoteTool", () => {
  it("should create with required fields", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com/endpoint",
      httpMethod: "POST",
    });
    expect(tool.componentType).toBe("RemoteTool");
    expect(tool.name).toBe("api-tool");
    expect(tool.url).toBe("https://api.example.com/endpoint");
    expect(tool.httpMethod).toBe("POST");
  });

  it("should infer inputs from URL placeholders", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com/{{resource}}/{{id}}",
      httpMethod: "GET",
    });
    expect(tool.inputs).toBeDefined();
    const titles = tool.inputs!.map((i) => i.title);
    expect(titles).toContain("resource");
    expect(titles).toContain("id");
  });

  it("should infer inputs from data placeholders", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com",
      httpMethod: "POST",
      data: { key: "{{api_key}}", query: "{{search_query}}" },
    });
    const titles = tool.inputs!.map((i) => i.title);
    expect(titles).toContain("api_key");
    expect(titles).toContain("search_query");
  });

  it("should infer inputs from queryParams placeholders", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com",
      httpMethod: "GET",
      queryParams: { q: "{{query}}" },
    });
    const titles = tool.inputs!.map((i) => i.title);
    expect(titles).toContain("query");
  });

  it("should infer inputs from headers placeholders", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com",
      httpMethod: "GET",
      headers: { Authorization: "Bearer {{token}}" },
    });
    const titles = tool.inputs!.map((i) => i.title);
    expect(titles).toContain("token");
  });

  it("should use custom inputs when provided", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com/{{resource}}",
      httpMethod: "GET",
      inputs: [stringProperty({ title: "custom_input" })],
    });
    expect(tool.inputs).toHaveLength(1);
    expect(tool.inputs![0]!.title).toBe("custom_input");
  });

  it("should have empty inputs when no placeholders exist", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com/fixed",
      httpMethod: "GET",
    });
    expect(tool.inputs).toEqual([]);
  });

  it("should default data/queryParams/headers to empty objects", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com",
      httpMethod: "GET",
    });
    expect(tool.data).toEqual({});
    expect(tool.queryParams).toEqual({});
    expect(tool.headers).toEqual({});
  });

  it("should be frozen", () => {
    const tool = createRemoteTool({
      name: "api-tool",
      url: "https://api.example.com",
      httpMethod: "GET",
    });
    expect(Object.isFrozen(tool)).toBe(true);
  });
});
