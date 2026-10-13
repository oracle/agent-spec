import { describe, expect, it } from "vitest";
import {
  createClientTool,
  createServerTool,
  integerProperty,
  stringProperty,
} from "../../../src/index.js";
import {
  defaultMastraToolResolver,
  MissingMastraToolExecutorError,
  propertiesToMastraJsonSchema,
  UnsupportedMastraToolError,
} from "../../../src/adapters/mastra/index.js";

describe("Mastra tool resolver", () => {
  it("maps properties to a Mastra-compatible object JSON schema", () => {
    expect(
      propertiesToMastraJsonSchema([
        stringProperty({ title: "query" }),
        integerProperty({ title: "limit" }),
      ]),
    ).toEqual({
      type: "object",
      properties: {
        query: { title: "query", type: "string" },
        limit: { title: "limit", type: "integer" },
      },
      required: ["query", "limit"],
      additionalProperties: false,
    });
  });

  it("does not require properties that define Agent Spec defaults", () => {
    expect(
      propertiesToMastraJsonSchema([
        stringProperty({ title: "city", default: "zurich" }),
        integerProperty({ title: "limit" }),
      ]),
    ).toEqual({
      type: "object",
      properties: {
        city: { title: "city", default: "zurich", type: "string" },
        limit: { title: "limit", type: "integer" },
      },
      required: ["limit"],
      additionalProperties: false,
    });
  });

  it("wraps ServerTool registry executors with Agent Spec context", async () => {
    const tool = createServerTool({
      name: "lookup",
      description: "Look up an item",
      inputs: [stringProperty({ title: "query" })],
      outputs: [stringProperty({ title: "answer" })],
      requiresConfirmation: true,
    });

    const target = defaultMastraToolResolver(tool, {
      toolRegistry: {
        lookup: (input, context) => ({
          input,
          toolName: context.agentSpecTool.name,
          mastraContext: context.mastraContext,
        }),
      },
    });

    expect(target).toMatchObject({
      id: "lookup",
      description: "Look up an item",
      requireApproval: true,
      inputSchema: {
        type: "object",
        properties: {
          query: { title: "query", type: "string" },
        },
        required: ["query"],
        additionalProperties: false,
      },
      outputSchema: {
        type: "object",
        properties: {
          answer: { title: "answer", type: "string" },
        },
        required: ["answer"],
        additionalProperties: false,
      },
    });

    await expect(
      Promise.resolve(target.execute?.({ query: "x" }, { runId: "run-1" })),
    ).resolves.toEqual({
      input: { query: "x" },
      toolName: "lookup",
      mastraContext: { runId: "run-1" },
    });
  });

  it("allows registry lookup by Agent Spec tool id", async () => {
    const tool = createServerTool({
      id: "tool-id",
      name: "lookup",
    });

    const target = defaultMastraToolResolver(tool, {
      toolRegistry: {
        "tool-id": () => "ok",
      },
    });

    await expect(Promise.resolve(target.execute?.({}, undefined))).resolves.toBe(
      "ok",
    );
  });

  it("fails when a ServerTool has no registered executor", () => {
    const tool = createServerTool({ name: "lookup" });

    expect(() => defaultMastraToolResolver(tool, {})).toThrow(
      MissingMastraToolExecutorError,
    );
  });

  it("fails explicitly for non-server tools", () => {
    const tool = createClientTool({ name: "client-input" });

    expect(() => defaultMastraToolResolver(tool, {})).toThrow(
      UnsupportedMastraToolError,
    );
  });
});
