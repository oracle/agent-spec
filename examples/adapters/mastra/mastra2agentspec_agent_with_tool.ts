/**
 * Mastra -> Agent Spec example.
 *
 * Exports a serializable Mastra-style agent config into Agent Spec YAML using
 * the TypeScript Mastra adapter.
 */
import {
  AgentSpecExporter,
} from "../../../tsagentspec/src/adapters/mastra/index.js";

const mastraWeatherAgent = {
  id: "mastra-weather-agent",
  name: "mastra_weather_agent",
  description: "Mastra-style weather agent exported to Agent Spec.",
  instructions: "Use the weather tool when the user asks for current weather.",
  metadata: {
    framework: "mastra",
    example: "mastra-to-agentspec",
  },
  model: {
    provider: "openai-compatible",
    modelId: "oci/openai.gpt-5.4-mini",
    url: "https://example-llm-endpoint.invalid/v1",
  },
  tools: {
    get_current_weather: {
      id: "get_current_weather",
      description: "Get current weather for a city.",
      inputSchema: {
        type: "object",
        properties: {
          city: {
            type: "string",
            description: "City or place name.",
          },
        },
        required: ["city"],
        additionalProperties: false,
      },
      outputSchema: {
        type: "object",
        properties: {
          weather_report: {
            type: "string",
            description: "Weather report for the requested city.",
          },
        },
        required: ["weather_report"],
        additionalProperties: false,
      },
    },
  },
};

const exporter = new AgentSpecExporter();
const agent = exporter.toAgent(mastraWeatherAgent);
const yaml = exporter.toYaml(mastraWeatherAgent);

console.log("Exported Agent Spec agent:", agent.name);
console.log("Exported tools:", agent.tools.map((tool) => tool.name).join(", "));
console.log("Agent Spec YAML:");
console.log(yaml);
