/**
 * Example 7: A2A (Agent-to-Agent) and Remote Agents
 *
 * Demonstrates connecting to remote agents via the A2A protocol
 * and defining remote agent placeholders.
 */
import {
  createA2AAgent,
  createA2AConnectionConfig,
  createRemoteAgent,
  createSwarm,
  createAgent,
  createVllmConfig,
  stringProperty,
  HandoffMode,
  AgentSpecSerializer,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

// =============================================
// RemoteAgent: a placeholder for an external agent
// =============================================

const externalAnalyzer = createRemoteAgent({
  name: "external-data-analyzer",
  description: "A remotely-hosted data analysis agent",
  inputs: [stringProperty({ title: "dataset_url" })],
  outputs: [stringProperty({ title: "analysis_summary" })],
});

console.log("RemoteAgent:", externalAnalyzer.name);
console.log("Type:", externalAnalyzer.componentType);

// =============================================
// A2A Agent: connect to a remote agent via HTTP
// =============================================

const connectionConfig = createA2AConnectionConfig({
  name: "translator-connection",
  timeout: 30,
  headers: { "X-Client-Id": "my-orchestrator" },
  verify: true,
});

const remoteTranslator = createA2AAgent({
  name: "translation-agent",
  description: "A remote agent that translates text between languages",
  agentUrl: "https://agents.example.com/translator",
  connectionConfig,
  sessionParameters: {
    timeout: 60,
    pollInterval: 2,
    maxRetries: 5,
  },
  inputs: [
    stringProperty({ title: "text" }),
    stringProperty({ title: "target_language" }),
  ],
  outputs: [stringProperty({ title: "translated_text" })],
});

console.log("\nA2A Agent:", remoteTranslator.name);
console.log("URL:", remoteTranslator.agentUrl);

// =============================================
// Compose with local agents in a swarm
// =============================================

const localAgent = createAgent({
  name: "coordinator",
  llmConfig,
  systemPrompt:
    "You coordinate between local processing and remote services. " +
    "Use the translation agent for multilingual content.",
});

const hybridSwarm = createSwarm({
  name: "hybrid-swarm",
  firstAgent: localAgent,
  relationships: [
    [localAgent, remoteTranslator],
    [remoteTranslator, localAgent],
  ],
  handoff: HandoffMode.OPTIONAL,
});

console.log("\nHybrid swarm:", hybridSwarm.name);
console.log("Mixes local and A2A agents");

const serializer = new AgentSpecSerializer();
console.log("\n--- Hybrid swarm (YAML) ---");
console.log(serializer.toYaml(hybridSwarm));
