/**
 * Example 1: Basic Agent
 *
 * Creates a simple conversational agent with an LLM configuration and
 * system prompt. Demonstrates template variable auto-inference.
 */
import {
  createAgent,
  createVllmConfig,
  createOllamaConfig,
  stringProperty,
  AgentSpecSerializer,
} from "agentspec";

// --- LLM configurations ---

// vLLM (self-hosted)
const vllmConfig = createVllmConfig({
  name: "local-vllm",
  url: "http://localhost:8000",
  modelId: "meta-llama/Llama-3-70B-Instruct",
  defaultGenerationParameters: {
    maxTokens: 2048,
    temperature: 0.7,
  },
});

// Ollama (local)
const ollamaConfig = createOllamaConfig({
  name: "local-ollama",
  url: "http://localhost:11434",
  modelId: "llama3",
});

// --- Create an agent ---

// Template variables like {{topic}} are automatically extracted as inputs.
const agent = createAgent({
  name: "research-assistant",
  description: "A helpful research assistant that specializes in a given topic",
  llmConfig: vllmConfig,
  systemPrompt:
    "You are an expert research assistant specializing in {{topic}}. " +
    "Provide detailed, well-sourced answers. Always cite your reasoning.",
  humanInTheLoop: false,
});

// The agent's inputs are auto-inferred from the {{topic}} placeholder.
console.log("Agent:", agent.name);
console.log("Component type:", agent.componentType);
console.log("Auto-inferred inputs:", agent.inputs?.map((i) => i.title));
// => ["topic"]

// You can also provide explicit inputs/outputs.
const agentWithExplicitIO = createAgent({
  name: "qa-agent",
  llmConfig: ollamaConfig,
  systemPrompt: "Answer questions about {{subject}} clearly and concisely.",
  inputs: [
    stringProperty({ title: "subject", default: "computer science" }),
    stringProperty({ title: "difficulty_level" }),
  ],
  outputs: [stringProperty({ title: "answer" })],
});

console.log(
  "\nExplicit inputs:",
  agentWithExplicitIO.inputs?.map((i) => i.title),
);

// --- Serialize to YAML ---

const serializer = new AgentSpecSerializer();
const yaml = serializer.toYaml(agent);
console.log("\n--- Serialized YAML ---");
console.log(yaml);

// Serialize to JSON (with pretty-printing)
const json = serializer.toJson(agent, { indent: 2 });
console.log("--- Serialized JSON ---");
console.log(json);
