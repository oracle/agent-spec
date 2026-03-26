/**
 * Example 2: Tools
 *
 * Demonstrates the different tool types: ServerTool, ClientTool,
 * RemoteTool, and BuiltinTool. Shows how to attach tools to an agent.
 */
import {
  createAgent,
  createVllmConfig,
  createServerTool,
  createClientTool,
  createRemoteTool,
  createBuiltinTool,
  stringProperty,
  booleanProperty,
  integerProperty,
  numberProperty,
  AgentSpecSerializer,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

// --- ServerTool: executed by the orchestrator runtime ---

const searchTool = createServerTool({
  name: "web_search",
  description: "Search the web for information",
  inputs: [
    stringProperty({ title: "query", description: "The search query" }),
    integerProperty({ title: "max_results", default: 5 }),
  ],
  outputs: [stringProperty({ title: "results" })],
});

// --- ClientTool: executed on the client side ---

const displayTool = createClientTool({
  name: "display_chart",
  description: "Display a chart to the user",
  inputs: [
    stringProperty({ title: "chart_type", description: "bar, line, or pie" }),
    stringProperty({ title: "data_points" }),
  ],
  outputs: [
    booleanProperty({ title: "displayed", description: "Whether the chart was shown" }),
  ],
});

// --- RemoteTool: calls an external HTTP API ---
// Template variables in url, data, and headers are auto-extracted as inputs.

const weatherTool = createRemoteTool({
  name: "get_weather",
  description: "Get current weather for a city",
  url: "https://api.weather.example.com/v1/current",
  httpMethod: "GET",
  queryParams: { city: "{{city_name}}", units: "metric" },
  headers: { "X-Api-Version": "2" },
  outputs: [
    numberProperty({ title: "temperature" }),
    stringProperty({ title: "condition" }),
  ],
});

// Inputs are auto-inferred from {{city_name}} in queryParams.
console.log("RemoteTool auto-inferred inputs:", weatherTool.inputs?.map((i) => i.title));
// => ["city_name"]

const newsletterTool = createRemoteTool({
  name: "subscribe_newsletter",
  description: "Subscribe a user to a city newsletter",
  url: "https://api.example.com/subscribe",
  httpMethod: "POST",
  data: {
    email: "{{user_email}}",
    city: "{{city_name}}",
    preferences: { format: "html" },
  },
  sensitiveHeaders: { Authorization: "Bearer secret-token" }, // excluded from serialization
});

console.log(
  "Newsletter auto-inferred inputs:",
  newsletterTool.inputs?.map((i) => i.title),
);

// --- BuiltinTool: a framework-provided tool ---

const builtinTool = createBuiltinTool({
  name: "code_interpreter",
  description: "Execute Python code in a sandbox",
  toolType: "orchestrator_builtin",
  configuration: { timeout: 30, memory_limit: "256MB" },
  executorName: "sandbox_executor",
  toolVersion: "2.0",
});

// --- Attach tools to an agent ---

const agent = createAgent({
  name: "assistant",
  llmConfig,
  systemPrompt: "You are a helpful assistant with access to various tools.",
  tools: [searchTool, displayTool, weatherTool, builtinTool],
});

console.log(`Agent "${agent.name}" has ${agent.tools.length} tools:`);
for (const tool of agent.tools) {
  console.log(`  - ${tool.name} (${tool.componentType})`);
}

// --- Serialize ---

const serializer = new AgentSpecSerializer();
console.log("\n--- Agent with tools (YAML) ---");
console.log(serializer.toYaml(agent));
