/**
 * Example 4: Flows
 *
 * Demonstrates building workflows using the FlowBuilder, including
 * linear flows, branching, data flow edges, and manual construction.
 */
import {
  createAgent,
  createVllmConfig,
  createLlmNode,
  createToolNode,
  createAgentNode,
  createServerTool,
  FlowBuilder,
  stringProperty,
  AgentSpecSerializer,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

// =============================================
// Linear flow using FlowBuilder.buildLinearFlow
// =============================================

const extractNode = createLlmNode({
  name: "extract-entities",
  llmConfig,
  promptTemplate: "Extract key entities from: {{user_text}}",
});

const summarizeNode = createLlmNode({
  name: "summarize",
  llmConfig,
  promptTemplate: "Summarize the following entities: {{entities}}",
});

// buildLinearFlow auto-creates StartNode and EndNode, infers inputs/outputs.
const linearFlow = FlowBuilder.buildLinearFlow({
  name: "extract-and-summarize",
  nodes: [extractNode, summarizeNode],
  dataFlowEdges: [
    // Pass generated_text from extract → entities input on summarize
    [extractNode, summarizeNode, "generated_text", "entities"],
  ],
});

console.log("Linear flow:", linearFlow.name);
console.log("Nodes:", linearFlow.nodes.length);
console.log("Inputs:", linearFlow.inputs?.map((i) => i.title));

// =============================================
// Flow with branching using FlowBuilder
// =============================================

const classifierNode = createLlmNode({
  name: "classify-intent",
  llmConfig,
  promptTemplate: "Classify the user's intent: {{user_message}}",
});

const questionHandler = createLlmNode({
  name: "handle-question",
  llmConfig,
  promptTemplate: "Answer the question thoroughly.",
});

const complaintHandler = createLlmNode({
  name: "handle-complaint",
  llmConfig,
  promptTemplate: "Address the complaint empathetically and offer solutions.",
});

const generalHandler = createLlmNode({
  name: "handle-general",
  llmConfig,
  promptTemplate: "Respond to the general message.",
});

const branchingFlow = (() => {
  const builder = new FlowBuilder();

  builder.addNode(classifierNode);
  builder.addNode(questionHandler);
  builder.addNode(complaintHandler);
  builder.addNode(generalHandler);

  builder.setEntryPoint("classify-intent", [
    stringProperty({ title: "user_message" }),
  ]);

  // Branch based on the classifier's output
  builder.addConditional(
    "classify-intent",
    "generated_text",
    {
      question: "handle-question",
      complaint: "handle-complaint",
    },
    "handle-general", // default branch
  );

  builder.setFinishPoints([
    "handle-question",
    "handle-complaint",
    "handle-general",
  ]);

  return builder.build("intent-router");
})();

console.log("\nBranching flow:", branchingFlow.name);
console.log("Nodes:", branchingFlow.nodes.length);
console.log(
  "Control edges:",
  branchingFlow.controlFlowConnections.length,
);

// =============================================
// Flow with tool and agent nodes
// =============================================

const lookupTool = createServerTool({
  name: "database_lookup",
  description: "Look up a record in the database",
  inputs: [stringProperty({ title: "record_id" })],
  outputs: [stringProperty({ title: "record_data" })],
});

const agent = createAgent({
  name: "analysis-agent",
  llmConfig,
  systemPrompt: "Analyze data and provide insights.",
});

const lookupNode = createToolNode({
  name: "lookup-step",
  tool: lookupTool,
});

const analysisNode = createAgentNode({
  name: "analysis-step",
  agent,
});

const formatNode = createLlmNode({
  name: "format-output",
  llmConfig,
  promptTemplate: "Format the analysis into a report: {{analysis}}",
});

const pipelineFlow = (() => {
  const builder = new FlowBuilder();

  builder.addNode(lookupNode);
  builder.addNode(analysisNode);
  builder.addNode(formatNode);

  builder.setEntryPoint("lookup-step", [
    stringProperty({ title: "record_id" }),
  ]);

  builder.addEdge("lookup-step", "analysis-step");
  builder.addEdge("analysis-step", "format-output");

  // Pass data between nodes
  builder.addDataEdge(
    "lookup-step",
    "analysis-step",
    "record_data",
  );
  builder.addDataEdge(
    "analysis-step",
    "format-output",
    ["output", "analysis"],
  );

  builder.setFinishPoints("format-output", [
    stringProperty({ title: "report" }),
  ]);

  return builder.build("data-pipeline");
})();

console.log("\nPipeline flow:", pipelineFlow.name);
console.log("Nodes:", pipelineFlow.nodes.length);

// --- Serialize ---

const serializer = new AgentSpecSerializer();
console.log("\n--- Branching flow (YAML) ---");
console.log(serializer.toYaml(branchingFlow));
