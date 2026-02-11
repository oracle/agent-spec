import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createVllmConfig,
  createServerTool,
  createStartNode,
  createEndNode,
  createToolNode,
  createControlFlowEdge,
  createFlow,
  stringProperty,
} from "../../src/index.js";

describe("$component_ref", () => {
  describe("shared tool used by multiple agents in a flow", () => {
    it("should produce $component_ref for shared components", () => {
      const serializer = new AgentSpecSerializer();

      const sharedTool = createServerTool({
        name: "shared-tool",
        inputs: [stringProperty({ title: "input" })],
      });

      const agent1 = createAgent({
        name: "agent1",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm1",
          url: "http://localhost",
          modelId: "gpt-4",
        }),
        systemPrompt: "Agent 1",
        tools: [sharedTool],
      });

      const agent2 = createAgent({
        name: "agent2",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm2",
          url: "http://localhost",
          modelId: "gpt-4",
        }),
        systemPrompt: "Agent 2",
        tools: [sharedTool],
      });

      // Create a flow with both agents sharing the same tool
      const start = createStartNode({ name: "start" });
      const end = createEndNode({ name: "end" });
      const toolNode1 = createToolNode({ name: "tool1", tool: sharedTool });
      const toolNode2 = createToolNode({ name: "tool2", tool: sharedTool });
      const e1 = createControlFlowEdge({
        name: "e1",
        fromNode: start,
        toNode: toolNode1,
      });
      const e2 = createControlFlowEdge({
        name: "e2",
        fromNode: toolNode1,
        toNode: toolNode2,
      });
      const e3 = createControlFlowEdge({
        name: "e3",
        fromNode: toolNode2,
        toNode: end,
      });
      const flow = createFlow({
        name: "ref-flow",
        startNode: start,
        nodes: [start, toolNode1, toolNode2, end],
        controlFlowConnections: [e1, e2, e3],
      });

      const json = serializer.toJson(flow) as string;
      const parsed = JSON.parse(json);

      // The shared tool should appear as a $component_ref somewhere
      const jsonStr = JSON.stringify(parsed);
      expect(jsonStr).toContain("$component_ref");
    });
  });

  describe("disaggregated components", () => {
    it("should use $component_ref for disaggregated llm config", () => {
      const serializer = new AgentSpecSerializer();
      const llmConfig = createVllmConfig({
        name: "shared-llm",
        url: "http://localhost:8000",
        modelId: "llama",
      });
      const agent = createAgent({
        name: "agent",
        llmConfig,
        systemPrompt: "Hello",
      });

      const [mainDict, disagDict] = serializer.toDict(agent, {
        disaggregatedComponents: [llmConfig],
        exportDisaggregatedComponents: true,
      }) as [Record<string, unknown>, Record<string, unknown>];

      // Main dict should use $component_ref for llm_config
      const llmField = mainDict["llm_config"] as Record<string, unknown>;
      expect(llmField["$component_ref"]).toBe(llmConfig.id);

      // Disaggregated dict should have the full component
      const refs = disagDict["$referenced_components"] as Record<string, unknown>;
      const refLlm = refs[llmConfig.id] as Record<string, unknown>;
      expect(refLlm["component_type"]).toBe("VllmConfig");
    });

    it("should round-trip disaggregated components", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();

      const llmConfig = createVllmConfig({
        name: "shared-llm",
        url: "http://localhost:8000",
        modelId: "llama",
      });
      const agent = createAgent({
        name: "agent",
        llmConfig,
        systemPrompt: "Hello",
      });

      const [mainJson, disagJson] = serializer.toJson(agent, {
        disaggregatedComponents: [llmConfig],
        exportDisaggregatedComponents: true,
      }) as [string, string];

      // Load disaggregated first
      const loadedComponents = deserializer.fromJson(disagJson, {
        importOnlyReferencedComponents: true,
      }) as Record<string, Record<string, unknown>>;

      const registry = new Map<string, Record<string, unknown>>();
      for (const [id, comp] of Object.entries(loadedComponents)) {
        registry.set(id, comp as any);
      }

      // Load main with registry
      const result = deserializer.fromJson(mainJson, {
        componentsRegistry: registry as any,
      }) as Record<string, unknown>;

      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("agent");
      const llm = result["llmConfig"] as Record<string, unknown>;
      expect(llm["componentType"]).toBe("VllmConfig");
      expect(llm["modelId"]).toBe("llama");
    });
  });
});
