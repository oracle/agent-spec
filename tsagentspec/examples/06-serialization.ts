/**
 * Example 6: Serialization and Deserialization
 *
 * Demonstrates JSON/YAML serialization, deserialization, camelCase mode,
 * disaggregated components, and versioning.
 */
import {
  createAgent,
  createVllmConfig,
  createServerTool,
  createSwarm,
  stringProperty,
  HandoffMode,
  AgentSpecSerializer,
  AgentSpecDeserializer,
  AgentSpecVersion,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

const tool = createServerTool({
  name: "lookup",
  description: "Look up information",
  inputs: [stringProperty({ title: "query" })],
});

const agent = createAgent({
  name: "demo-agent",
  llmConfig,
  systemPrompt: "You are a demo agent for {{topic}}.",
  tools: [tool],
  metadata: { version: "1.0", team: "platform" },
});

// =============================================
// Basic serialization
// =============================================

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

// YAML (default snake_case keys)
const yaml = serializer.toYaml(agent) as string;
console.log("--- YAML (snake_case) ---");
console.log(yaml);

// JSON (with indentation)
const json = serializer.toJson(agent, { indent: 2 }) as string;
console.log("--- JSON (snake_case) ---");
console.log(json);

// =============================================
// camelCase mode
// =============================================

// Serialize with camelCase field names (preserves JS convention)
const camelJson = serializer.toJson(agent, { camelCase: true, indent: 2 }) as string;
console.log("--- JSON (camelCase) ---");
console.log(camelJson);

// Deserialize camelCase JSON back
const fromCamel = deserializer.fromJson(camelJson, { camelCase: true });
console.log(
  "Round-trip (camelCase) OK:",
  (fromCamel as Record<string, unknown>)["name"] === "demo-agent",
);

// =============================================
// Disaggregated components
// =============================================

// When serializing complex structures (swarms, flows), you can export
// referenced components separately for modular storage.

const agentA = createAgent({
  name: "agent-a",
  llmConfig,
  systemPrompt: "Agent A.",
});
const agentB = createAgent({
  name: "agent-b",
  llmConfig,
  systemPrompt: "Agent B.",
});

const swarm = createSwarm({
  name: "demo-swarm",
  firstAgent: agentA,
  relationships: [[agentA, agentB]],
  handoff: HandoffMode.OPTIONAL,
});

// Export with disaggregated components: the main structure references
// components by ID, and the components are exported separately.
const [mainYaml, referencedYaml] = serializer.toYaml(swarm, {
  disaggregatedComponents: [agentA, agentB],
  exportDisaggregatedComponents: true,
}) as [string, string];

console.log("--- Main structure (references by ID) ---");
console.log(mainYaml);
console.log("--- Disaggregated components ---");
console.log(referencedYaml);

// First load the referenced components, then use them as a registry.
const referencedComponents = deserializer.fromYaml(referencedYaml, {
  importOnlyReferencedComponents: true,
}) as Record<string, { id: string; name: string; componentType: string }>;

const registry = new Map<string, typeof agentA>();
for (const [id, component] of Object.entries(referencedComponents)) {
  registry.set(id, component as typeof agentA);
}

const restoredSwarm = deserializer.fromYaml(mainYaml, {
  componentsRegistry: registry,
});
console.log(
  "Disaggregated round-trip OK:",
  (restoredSwarm as Record<string, unknown>)["name"] === "demo-swarm",
);

// =============================================
// Specifying agentspec version
// =============================================

// Pin to a specific spec version for compatibility.
const versionedYaml = serializer.toYaml(agent, {
  agentspecVersion: AgentSpecVersion.V25_4_0,
}) as string;
console.log("--- Versioned YAML (25.4.0) ---");
console.log(versionedYaml);

// =============================================
// Deserialization safety limits
// =============================================

// Configure max input size and recursion depth for untrusted input.
const safeDeserializer = new AgentSpecDeserializer({
  maxInputSize: 1_000_000, // 1 MB
  maxDepth: 50,
});

const safeResult = safeDeserializer.fromYaml(yaml);
console.log(
  "Safe deserialization OK:",
  (safeResult as Record<string, unknown>)["name"] === "demo-agent",
);
