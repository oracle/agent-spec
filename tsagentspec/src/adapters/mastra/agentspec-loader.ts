import { AgentSchema, type Agent } from "../../agents/index.js";
import type { ComponentBase } from "../../component.js";
import {
  AgentSpecDeserializer,
  type ComponentsRegistry,
  type DisaggregatedComponentsDict,
  type SerializedDict,
} from "../../serialization/index.js";
import { AgentSpecToMastraConverter } from "./mastra-converter.js";
import { InvalidMastraAgentSpecError } from "./errors.js";
import type { AgentSpecToMastraConversionOptions } from "./types.js";

export type AgentSpecDeserializeOptions = {
  componentsRegistry?: ComponentsRegistry;
  importOnlyReferencedComponents?: boolean;
  camelCase?: boolean;
};

export type AgentSpecReferencedComponentsOptions =
  AgentSpecDeserializeOptions & {
    importOnlyReferencedComponents: true;
  };

export type AgentSpecMainComponentOptions =
  AgentSpecDeserializeOptions & {
    importOnlyReferencedComponents?: false;
  };

export type AgentSpecLoaderOptions<
  TAgent = unknown,
  TTool = unknown,
> = AgentSpecToMastraConversionOptions<TAgent, TTool> & {
  deserializer?: AgentSpecDeserializer;
};

export class AgentSpecLoader<TAgent = unknown, TTool = unknown> {
  private readonly deserializer: AgentSpecDeserializer;
  private readonly converter: AgentSpecToMastraConverter<TAgent, TTool>;

  constructor(options: AgentSpecLoaderOptions<TAgent, TTool> = {}) {
    const { deserializer, ...conversionOptions } = options;
    this.deserializer = deserializer ?? new AgentSpecDeserializer();
    this.converter = new AgentSpecToMastraConverter(conversionOptions);
  }

  loadJson(
    json: string,
    options: AgentSpecReferencedComponentsOptions,
  ): ComponentsRegistry;

  loadJson(
    json: string,
    options?: AgentSpecMainComponentOptions,
  ): TAgent;

  loadJson(
    json: string,
    options?: AgentSpecDeserializeOptions,
  ): TAgent | ComponentsRegistry {
    return this.loadDeserialized(this.deserializer.fromJson(json, options), options);
  }

  loadYaml(
    yaml: string,
    options: AgentSpecReferencedComponentsOptions,
  ): ComponentsRegistry;

  loadYaml(
    yaml: string,
    options?: AgentSpecMainComponentOptions,
  ): TAgent;

  loadYaml(
    yaml: string,
    options?: AgentSpecDeserializeOptions,
  ): TAgent | ComponentsRegistry {
    return this.loadDeserialized(this.deserializer.fromYaml(yaml, options), options);
  }

  loadDict(
    dict: SerializedDict | DisaggregatedComponentsDict,
    options: AgentSpecReferencedComponentsOptions,
  ): ComponentsRegistry;

  loadDict(
    dict: SerializedDict | DisaggregatedComponentsDict,
    options?: AgentSpecMainComponentOptions,
  ): TAgent;

  loadDict(
    dict: SerializedDict | DisaggregatedComponentsDict,
    options?: AgentSpecDeserializeOptions,
  ): TAgent | ComponentsRegistry {
    return this.loadDeserialized(
      this.deserializer.fromJson(JSON.stringify(dict), options),
      options,
    );
  }

  loadComponent(component: ComponentBase): TAgent;

  loadComponent(component: Record<string, ComponentBase>): ComponentsRegistry;

  loadComponent(
    component: ComponentBase | Record<string, ComponentBase>,
  ): TAgent | ComponentsRegistry {
    if (!isComponentBase(component)) {
      return toComponentsRegistry(component);
    }

    return this.converter.convert(assertAgent(component));
  }

  private loadDeserialized(
    component: ComponentBase | Record<string, ComponentBase>,
    options?: AgentSpecDeserializeOptions,
  ): TAgent | ComponentsRegistry {
    if (options?.importOnlyReferencedComponents) {
      if (isComponentBase(component)) {
        throw new InvalidMastraAgentSpecError(
          "Expected referenced Agent Spec components, but received a root component.",
        );
      }
      return toComponentsRegistry(component);
    }

    if (!isComponentBase(component)) {
      throw new InvalidMastraAgentSpecError(
        "Expected a root Agent component, but received a component registry.",
      );
    }

    return this.loadComponent(component);
  }
}

const assertAgent = (
  component: ComponentBase,
): Agent => {
  if (component.componentType !== "Agent") {
    throw new InvalidMastraAgentSpecError(
      `Expected a root Agent component, but received ${component.componentType}.`,
    );
  }

  return AgentSchema.parse(component);
};

const toComponentsRegistry = (
  components: Record<string, ComponentBase>,
): ComponentsRegistry => new Map(Object.entries(components));

const isComponentBase = (
  value: ComponentBase | Record<string, ComponentBase>,
): value is ComponentBase => {
  const candidate = value as Partial<ComponentBase>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.name === "string" &&
    typeof candidate.componentType === "string"
  );
};
