/**
 * Curated repository-fixture round-trip tests.
 *
 * Supported surface: the 61 configs listed below are the stable CI contract.
 * This file does NOT guarantee that every historical or example fixture in the
 * repo round-trips — only the curated set here is covered.
 *
 * Three loading modes are used:
 *   - standard: single-file fromJson/fromYaml → toJson → fromJson
 *   - placeholder-resolved: [[...]] tokens replaced with dummy values before parsing
 *   - disaggregated: two-step API (importOnlyReferencedComponents + componentsRegistry)
 */

import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  type ComponentsRegistry,
  type ComponentBase,
} from "../src/index.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, "../..");

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

function readFixture(repoRelativePath: string): string {
  return readFileSync(resolve(REPO_ROOT, repoRelativePath), "utf-8");
}

/** Replace all [[PLACEHOLDER]] tokens with a dummy valid value. */
function resolvePlaceholders(content: string): string {
  return content.replace(/\[\[[^\]]+\]\]/g, "http://localhost:8000");
}

function roundTrip(content: string, parse: (s: string) => ComponentBase): void {
  const component = parse(content);
  expect(component.componentType).toBeDefined();
  const reserialized = serializer.toJson(component) as string;
  const reloaded = deserializer.fromJson(reserialized) as ComponentBase;
  expect(reloaded.componentType).toBe(component.componentType);
}

function roundTripJson(content: string): void {
  roundTrip(content, (s) => deserializer.fromJson(s) as ComponentBase);
}

function roundTripYaml(content: string): void {
  roundTrip(content, (s) => deserializer.fromYaml(s) as ComponentBase);
}

function roundTripDisaggregated(
  componentFileContent: string,
  mainFileContent: string,
  format: "json" | "yaml",
): void {
  const parse = format === "json"
    ? (s: string, opts?: object) => deserializer.fromJson(s, opts)
    : (s: string, opts?: object) => deserializer.fromYaml(s, opts);

  const importedComponents = parse(componentFileContent, {
    importOnlyReferencedComponents: true,
  }) as Record<string, ComponentBase>;

  const registry: ComponentsRegistry = new Map(Object.entries(importedComponents));

  const component = parse(mainFileContent, { componentsRegistry: registry }) as ComponentBase;
  expect(component.componentType).toBeDefined();

  const reserialized = serializer.toJson(component) as string;
  const reloaded = deserializer.fromJson(reserialized) as ComponentBase;
  expect(reloaded.componentType).toBe(component.componentType);
}

const EXAMPLES_DIR = "docs/pyagentspec/source/agentspec_config_examples";

const STANDARD_JSON_FIXTURES = [
  `${EXAMPLES_DIR}/agentspec_oracle_it_assistant.json`,
  `${EXAMPLES_DIR}/autogen_to_agentspec.json`,
  `${EXAMPLES_DIR}/ext_christmas_greetings_tutorial.json`,
  `${EXAMPLES_DIR}/ext_code_assistant_tutorial.json`,
  `${EXAMPLES_DIR}/ext_ops_assistant_tutorial_agent.json`,
  `${EXAMPLES_DIR}/ext_ops_assistant_tutorial_flow.json`,
  `${EXAMPLES_DIR}/ext_tutorial_cybersecurity_flow.json`,
  `${EXAMPLES_DIR}/howto_ag_ui.json`,
  `${EXAMPLES_DIR}/howto_agent_with_remote_tools.json`,
  `${EXAMPLES_DIR}/howto_agents.json`,
  `${EXAMPLES_DIR}/howto_catchexception.json`,
  `${EXAMPLES_DIR}/howto_flow_with_conditional_branches.json`,
  `${EXAMPLES_DIR}/howto_flowbuilder.json`,
  `${EXAMPLES_DIR}/howto_managerworkers.json`,
  `${EXAMPLES_DIR}/howto_mapnode.json`,
  `${EXAMPLES_DIR}/howto_mcp_agent.json`,
  `${EXAMPLES_DIR}/howto_mcp_flow.json`,
  `${EXAMPLES_DIR}/howto_parallelflownode.json`,
  `${EXAMPLES_DIR}/howto_structured_generation1.json`,
  `${EXAMPLES_DIR}/howto_structured_generation2.json`,
  `${EXAMPLES_DIR}/howto_structured_generation3.json`,
  `${EXAMPLES_DIR}/howto_summarization_transforms.json`,
  `${EXAMPLES_DIR}/howto_summary_flow.json`,
  `${EXAMPLES_DIR}/math_homework_agent.json`,
  `${EXAMPLES_DIR}/simple_agent_with_rag_tool.json`,
];

const STANDARD_YAML_FIXTURES = [
  `${EXAMPLES_DIR}/agentspec_oracle_it_assistant.yaml`,
  `${EXAMPLES_DIR}/autogen_to_agentspec.yaml`,
  `${EXAMPLES_DIR}/ext_christmas_greetings_tutorial.yaml`,
  `${EXAMPLES_DIR}/ext_code_assistant_tutorial.yaml`,
  `${EXAMPLES_DIR}/ext_ops_assistant_tutorial_agent.yaml`,
  `${EXAMPLES_DIR}/ext_ops_assistant_tutorial_flow.yaml`,
  `${EXAMPLES_DIR}/ext_tutorial_cybersecurity_flow.yaml`,
  `${EXAMPLES_DIR}/howto_ag_ui.yaml`,
  `${EXAMPLES_DIR}/howto_agent_with_remote_tools.yaml`,
  `${EXAMPLES_DIR}/howto_agents.yaml`,
  `${EXAMPLES_DIR}/howto_catchexception.yaml`,
  `${EXAMPLES_DIR}/howto_flow_with_conditional_branches.yaml`,
  `${EXAMPLES_DIR}/howto_flowbuilder.yaml`,
  `${EXAMPLES_DIR}/howto_managerworkers.yaml`,
  `${EXAMPLES_DIR}/howto_mapnode.yaml`,
  `${EXAMPLES_DIR}/howto_mcp_agent.yaml`,
  `${EXAMPLES_DIR}/howto_mcp_flow.yaml`,
  `${EXAMPLES_DIR}/howto_parallelflownode.yaml`,
  `${EXAMPLES_DIR}/howto_structured_generation1.yaml`,
  `${EXAMPLES_DIR}/howto_structured_generation2.yaml`,
  `${EXAMPLES_DIR}/howto_structured_generation3.yaml`,
  `${EXAMPLES_DIR}/howto_summary_flow.yaml`,
  `${EXAMPLES_DIR}/math_homework_agent.yaml`,
  `${EXAMPLES_DIR}/simple_agent_with_rag_tool.yaml`,
];

const ADAPTER_DIR = "pyagentspec/tests/adapters/langgraph/configs";

const PLACEHOLDER_JSON_FIXTURES = [
  `${ADAPTER_DIR}/haiku_without_a_flow.json`,
];

const PLACEHOLDER_YAML_FIXTURES = [
  `${ADAPTER_DIR}/ancestry_agent_with_client_tool.yaml`,
  `${ADAPTER_DIR}/swarm_calculator.yaml`,
  `${ADAPTER_DIR}/weather_agent_client_tool.yaml`,
  `${ADAPTER_DIR}/weather_agent_remote_tool.yaml`,
  `${ADAPTER_DIR}/weather_agent_server_tool.yaml`,
  `${ADAPTER_DIR}/weather_agent_with_outputs.yaml`,
  `${ADAPTER_DIR}/weather_ollama_agent.yaml`,
];

describe("Repo fixture round-trips", () => {
  describe("Standard JSON fixtures", () => {
    for (const fixture of STANDARD_JSON_FIXTURES) {
      it(fixture, () => {
        roundTripJson(readFixture(fixture));
      });
    }
  });

  describe("Standard YAML fixtures", () => {
    for (const fixture of STANDARD_YAML_FIXTURES) {
      it(fixture, () => {
        roundTripYaml(readFixture(fixture));
      });
    }
  });

  describe("Placeholder-resolved JSON fixtures", () => {
    for (const fixture of PLACEHOLDER_JSON_FIXTURES) {
      it(fixture, () => {
        roundTripJson(resolvePlaceholders(readFixture(fixture)));
      });
    }
  });

  describe("Placeholder-resolved YAML fixtures", () => {
    for (const fixture of PLACEHOLDER_YAML_FIXTURES) {
      it(fixture, () => {
        roundTripYaml(resolvePlaceholders(readFixture(fixture)));
      });
    }
  });

  describe("Disaggregated fixtures (two-step API)", () => {
    it("howto_disaggregated (JSON)", () => {
      roundTripDisaggregated(
        readFixture(`${EXAMPLES_DIR}/howto_disaggregated_component_config.json`),
        readFixture(`${EXAMPLES_DIR}/howto_disaggregated_main_config.json`),
        "json",
      );
    });

    it("howto_disaggregated (YAML)", () => {
      roundTripDisaggregated(
        readFixture(`${EXAMPLES_DIR}/howto_disaggregated_component_config.yaml`),
        readFixture(`${EXAMPLES_DIR}/howto_disaggregated_main_config.yaml`),
        "yaml",
      );
    });
  });
});
