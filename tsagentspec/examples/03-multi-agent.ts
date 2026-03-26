/**
 * Example 3: Multi-Agent Patterns
 *
 * Demonstrates Swarm, ManagerWorkers, and SpecializedAgent patterns
 * for building multi-agent systems.
 */
import {
  createAgent,
  createVllmConfig,
  createSwarm,
  createManagerWorkers,
  createSpecializedAgent,
  createAgentSpecializationParameters,
  createServerTool,
  stringProperty,
  HandoffMode,
  AgentSpecSerializer,
  AgentSpecDeserializer,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

// =============================================
// Pattern 1: Swarm — peer agents with handoffs
// =============================================

const triageAgent = createAgent({
  name: "triage",
  llmConfig,
  systemPrompt: "You triage customer requests and hand off to the right specialist.",
});

const billingAgent = createAgent({
  name: "billing-specialist",
  llmConfig,
  systemPrompt: "You handle billing inquiries, refunds, and payment issues.",
});

const technicalAgent = createAgent({
  name: "technical-support",
  llmConfig,
  systemPrompt: "You provide technical support and troubleshooting assistance.",
});

const supportSwarm = createSwarm({
  name: "customer-support-swarm",
  firstAgent: triageAgent,
  relationships: [
    [triageAgent, billingAgent],    // triage can hand off to billing
    [triageAgent, technicalAgent],  // triage can hand off to technical
    [billingAgent, triageAgent],    // billing can hand back to triage
    [technicalAgent, triageAgent],  // technical can hand back to triage
  ],
  handoff: HandoffMode.OPTIONAL,
});

console.log("Swarm:", supportSwarm.name);
console.log("First agent:", supportSwarm.firstAgent.name);
console.log("Relationships:", supportSwarm.relationships.length);

// =============================================
// Pattern 2: ManagerWorkers — hierarchical delegation
// =============================================

const projectManager = createAgent({
  name: "project-manager",
  llmConfig,
  systemPrompt:
    "You are a project manager. Break down tasks and delegate to workers. " +
    "Synthesize their results into a final deliverable.",
});

const researcher = createAgent({
  name: "researcher",
  llmConfig,
  systemPrompt: "You conduct research and gather information on assigned topics.",
  tools: [
    createServerTool({
      name: "search",
      description: "Search for information",
      inputs: [stringProperty({ title: "query" })],
      outputs: [stringProperty({ title: "results" })],
    }),
  ],
});

const writer = createAgent({
  name: "writer",
  llmConfig,
  systemPrompt: "You write clear, engaging content based on research findings.",
});

const reviewTeam = createManagerWorkers({
  name: "content-team",
  groupManager: projectManager,
  workers: [researcher, writer],
});

console.log("\nManagerWorkers:", reviewTeam.name);
console.log("Manager:", reviewTeam.groupManager.name);
console.log("Workers:", reviewTeam.workers.map((w) => w.name));

// =============================================
// Pattern 3: SpecializedAgent — reuse a base agent with customization
// =============================================

const baseAssistant = createAgent({
  name: "base-assistant",
  llmConfig,
  systemPrompt:
    "You are a helpful assistant for {{domain}}. " +
    "Be concise and provide actionable advice.",
});

// Specialize for finance
const financeParams = createAgentSpecializationParameters({
  name: "finance-specialization",
  additionalInstructions:
    "Focus on {{market}} market trends. " +
    "Always include risk disclaimers and cite data sources.",
  additionalTools: [
    createServerTool({
      name: "stock_lookup",
      description: "Look up current stock price",
      inputs: [stringProperty({ title: "ticker" })],
      outputs: [stringProperty({ title: "price" })],
    }),
  ],
});

const financeAgent = createSpecializedAgent({
  name: "finance-assistant",
  agent: baseAssistant,
  agentSpecializationParameters: financeParams,
});

// Inputs are merged and deduplicated from base + specialization.
console.log("\nSpecializedAgent:", financeAgent.name);
console.log(
  "Merged inputs:",
  financeAgent.inputs?.map((i) => i.title),
);
// => ["domain", "market"]

// =============================================
// Composing patterns: Swarm containing ManagerWorkers
// =============================================

const soloAgent = createAgent({
  name: "solo-creative",
  llmConfig,
  systemPrompt: "You handle creative writing tasks independently.",
});

const metaSwarm = createSwarm({
  name: "meta-organization",
  firstAgent: reviewTeam,      // a ManagerWorkers as the first agent
  relationships: [
    [reviewTeam, soloAgent],   // can hand off to the solo agent
    [soloAgent, reviewTeam],   // and back
  ],
});

console.log("\nComposite swarm:", metaSwarm.name);

// --- Round-trip serialization ---

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

const yaml = serializer.toYaml(supportSwarm) as string;
const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
console.log("\nRound-trip OK:", restored["name"] === "customer-support-swarm");
