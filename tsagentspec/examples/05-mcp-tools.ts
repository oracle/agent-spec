/**
 * Example 5: MCP (Model Context Protocol) Tools
 *
 * Demonstrates creating MCP tools with different transport types
 * and grouping them into toolboxes.
 */
import {
  createAgent,
  createVllmConfig,
  createMCPTool,
  createMCPToolSpec,
  createMCPToolBox,
  createStdioTransport,
  createSSETransport,
  createStreamableHTTPTransport,
  stringProperty,
  AgentSpecSerializer,
} from "agentspec";

const llmConfig = createVllmConfig({
  name: "model",
  url: "http://localhost:8000",
  modelId: "llama-3-70b",
});

// --- Transport configurations ---

// Stdio transport (for local MCP servers)
const stdioTransport = createStdioTransport({
  name: "filesystem-stdio",
  command: "npx",
  args: ["-y", "@modelcontextprotocol/server-filesystem"],
  env: { HOME: "/home/user" },
});

// SSE transport (Server-Sent Events)
const sseTransport = createSSETransport({
  name: "sse-server",
  url: "http://localhost:3001/sse",
});

// Streamable HTTP transport
const httpTransport = createStreamableHTTPTransport({
  name: "http-server",
  url: "http://localhost:3002/mcp",
});

// --- MCP Tools ---

// An individual MCP tool with explicit inputs/outputs
const fileReadTool = createMCPTool({
  name: "read_file",
  description: "Read the contents of a file",
  clientTransport: stdioTransport,
  inputs: [stringProperty({ title: "path", description: "File path to read" })],
  outputs: [stringProperty({ title: "content" })],
});

// MCP tool spec (defines the tool shape without transport)
const searchSpec = createMCPToolSpec({
  name: "search_documents",
  description: "Search through indexed documents",
  inputs: [
    stringProperty({ title: "query" }),
    stringProperty({ title: "collection", default: "default" }),
  ],
  outputs: [stringProperty({ title: "results" })],
});

// --- MCP Toolbox ---
// A toolbox groups multiple MCP tools behind a single transport.
// Use toolFilter to restrict which tools from the server are exposed.

const fileToolbox = createMCPToolBox({
  name: "filesystem-tools",
  description: "Tools for interacting with the local filesystem",
  clientTransport: stdioTransport,
  toolFilter: [
    createMCPToolSpec({
      name: "read_file",
      description: "Read a file",
      inputs: [stringProperty({ title: "path" })],
    }),
    createMCPToolSpec({
      name: "write_file",
      description: "Write content to a file",
      inputs: [
        stringProperty({ title: "path" }),
        stringProperty({ title: "content" }),
      ],
    }),
    createMCPToolSpec({
      name: "list_directory",
      description: "List files in a directory",
      inputs: [stringProperty({ title: "path" })],
    }),
  ],
});

// --- Agent with MCP tools and toolboxes ---

const agent = createAgent({
  name: "filesystem-agent",
  llmConfig,
  systemPrompt: "You help users manage their files and documents.",
  tools: [fileReadTool],
  toolboxes: [fileToolbox],
});

console.log(`Agent "${agent.name}" has:`);
console.log(`  ${agent.tools.length} direct tool(s)`);
console.log(`  ${agent.toolboxes?.length ?? 0} toolbox(es)`);

const serializer = new AgentSpecSerializer();
console.log("\n--- Agent with MCP tools (YAML) ---");
console.log(serializer.toYaml(agent));
