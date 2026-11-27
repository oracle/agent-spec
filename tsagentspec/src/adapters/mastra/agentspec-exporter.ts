import type { Agent } from "../../agents/index.js";
import type { Flow } from "../../flows/index.js";
import { AgentSpecSerializer } from "../../serialization/index.js";
import {
  MastraToAgentSpecConverter,
  type AgentSpecExportedComponent,
  type MastraToAgentSpecConversionOptions,
} from "./agentspec-converter.js";

export type AgentSpecExporterOptions = MastraToAgentSpecConversionOptions;

export class AgentSpecExporter {
  private readonly serializer: AgentSpecSerializer;
  private readonly converter: MastraToAgentSpecConverter;

  constructor(options: AgentSpecExporterOptions = {}) {
    this.serializer = new AgentSpecSerializer();
    this.converter = new MastraToAgentSpecConverter(options);
  }

  get runtimeToAgentSpecConverter(): MastraToAgentSpecConverter {
    return this.converter;
  }

  toComponent(input: unknown): AgentSpecExportedComponent {
    return this.converter.convert(input);
  }

  toAgent(input: unknown): Agent {
    return this.converter.toAgent(input);
  }

  toFlow(input: unknown): Flow {
    return this.converter.toFlow(input);
  }

  toJson(
    input: unknown,
    options?: Parameters<AgentSpecSerializer["toJson"]>[1],
  ): ReturnType<AgentSpecSerializer["toJson"]> {
    return this.serializer.toJson(this.toComponent(input), options);
  }

  toYaml(
    input: unknown,
    options?: Parameters<AgentSpecSerializer["toYaml"]>[1],
  ): ReturnType<AgentSpecSerializer["toYaml"]> {
    return this.serializer.toYaml(this.toComponent(input), options);
  }
}
