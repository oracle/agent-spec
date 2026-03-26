/**
 * AgentSpecSerializer - main entry point for component serialization.
 *
 * Provides toJson and toYaml methods.
 */
import YAML from "yaml";

import type { AgentSpecVersion } from "../versioning.js";
import type { ComponentBase } from "../component.js";
import type { ComponentSerializationPlugin } from "./serialization-plugin.js";
import { SerializationContext } from "./serialization-context.js";
import { BuiltinsComponentSerializationPlugin } from "./builtin-serialization-plugin.js";
import type { SerializedDict, DisaggregatedComponentsDict } from "./types.js";

export class AgentSpecSerializer {
  private plugins: ComponentSerializationPlugin[];

  constructor(plugins?: ComponentSerializationPlugin[]) {
    this.plugins = [...(plugins ?? [])];

    // Always add the builtin plugin at the end
    this.plugins.push(new BuiltinsComponentSerializationPlugin());

    // Validate no plugin collisions by building a context
    new SerializationContext(this.plugins);
  }

  /** Serialize a component to a plain dict (internal) */
  private _toDict(
    component: ComponentBase,
    options?: {
      agentspecVersion?: AgentSpecVersion;
      disaggregatedComponents?: ComponentBase[];
      exportDisaggregatedComponents?: boolean;
      camelCase?: boolean;
    },
  ): SerializedDict | [SerializedDict, DisaggregatedComponentsDict] {
    const opts = options ?? {};
    const disaggregated = opts.disaggregatedComponents ?? [];
    const exportDisag = opts.exportDisaggregatedComponents ?? false;
    const useCamelCase = opts.camelCase ?? false;

    // Build ID mapping for disaggregated components
    const componentsIdMapping = new Map<string, string>();
    for (const disag of disaggregated) {
      componentsIdMapping.set(disag.id, disag.id);
    }

    // Serialize disaggregated components separately
    const disaggregatedDict: Record<string, SerializedDict> = {};
    for (const disag of disaggregated) {
      if (disag === component) {
        throw new Error("Cannot disaggregate the root component");
      }
      const disagCtx = new SerializationContext(
        this.plugins,
        opts.agentspecVersion,
        undefined,
        undefined,
        useCamelCase,
      );
      const dump = disagCtx.saveToDict(disag, opts.agentspecVersion);
      disaggregatedDict[disag.id] = dump;
    }

    // Serialize the main component
    const resolvedComponents = new Map<string, SerializedDict>();
    for (const [id, dump] of Object.entries(disaggregatedDict)) {
      resolvedComponents.set(id, dump);
    }
    const mainCtx = new SerializationContext(
      this.plugins,
      opts.agentspecVersion,
      resolvedComponents,
      componentsIdMapping,
      useCamelCase,
    );
    const mainDump = mainCtx.saveToDict(component, opts.agentspecVersion);

    if (!exportDisag) {
      return mainDump;
    }

    return [
      mainDump,
      { $referenced_components: disaggregatedDict },
    ];
  }

  /** Serialize a component to a JSON string */
  toJson(
    component: ComponentBase,
    options?: {
      agentspecVersion?: AgentSpecVersion;
      disaggregatedComponents?: ComponentBase[];
      exportDisaggregatedComponents?: boolean;
      indent?: number;
      camelCase?: boolean;
    },
  ): string | [string, string] {
    const indent = options?.indent ?? 2;
    const result = this._toDict(component, options);

    if (Array.isArray(result)) {
      return [
        JSON.stringify(result[0], null, indent),
        JSON.stringify(result[1], null, indent),
      ];
    }
    return JSON.stringify(result, null, indent);
  }

  /** Serialize a component to a YAML string */
  toYaml(
    component: ComponentBase,
    options?: {
      agentspecVersion?: AgentSpecVersion;
      disaggregatedComponents?: ComponentBase[];
      exportDisaggregatedComponents?: boolean;
      camelCase?: boolean;
    },
  ): string | [string, string] {
    const result = this._toDict(component, options);

    if (Array.isArray(result)) {
      return [
        YAML.stringify(result[0], { sortMapEntries: false }),
        YAML.stringify(result[1], { sortMapEntries: false }),
      ];
    }
    return YAML.stringify(result, { sortMapEntries: false });
  }
}
