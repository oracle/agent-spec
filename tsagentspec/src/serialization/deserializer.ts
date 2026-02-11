/**
 * AgentSpecDeserializer - main entry point for component deserialization.
 *
 * Provides fromDict, fromJson, and fromYaml methods.
 */
import YAML from "yaml";

import type { ComponentBase } from "../component.js";
import type { ComponentDeserializationPlugin } from "./deserialization-plugin.js";
import { DeserializationContext } from "./deserialization-context.js";
import { BuiltinsComponentDeserializationPlugin } from "./builtin-deserialization-plugin.js";
import type { ComponentAsDict, ComponentsRegistry } from "./types.js";

export class AgentSpecDeserializer {
  private plugins: ComponentDeserializationPlugin[];

  constructor(plugins?: ComponentDeserializationPlugin[]) {
    this.plugins = [...(plugins ?? [])];

    // Always add the builtin plugin at the end
    this.plugins.push(new BuiltinsComponentDeserializationPlugin());

    // Validate no plugin collisions
    new DeserializationContext(this.plugins);
  }

  /** Deserialize a component from a plain dict */
  fromDict(
    data: ComponentAsDict,
    options?: {
      componentsRegistry?: ComponentsRegistry;
      importOnlyReferencedComponents?: boolean;
    },
  ): ComponentBase | Record<string, ComponentBase> {
    const opts = options ?? {};
    const importOnly = opts.importOnlyReferencedComponents ?? false;
    const allKeys = new Set(Object.keys(data));

    if (!importOnly) {
      // Loading as a main component
      if (allKeys.size === 1 && allKeys.has("$referenced_components")) {
        throw new Error(
          "Cannot deserialize: content only has '$referenced_components'. " +
            "Set importOnlyReferencedComponents=true to load disaggregated configs.",
        );
      }

      this.checkMissingReferences(data, opts.componentsRegistry);

      const ctx = new DeserializationContext(this.plugins);
      return ctx.loadConfigDict(data, opts.componentsRegistry);
    }

    // Loading disaggregated components only
    if (!allKeys.has("$referenced_components")) {
      throw new Error(
        "Disaggregated config should have '$referenced_components' field.",
      );
    }
    if (allKeys.size !== 1) {
      throw new Error(
        `Disaggregated config should only have '$referenced_components' field, ` +
          `but got: ${[...allKeys].join(", ")}`,
      );
    }

    const refs = data["$referenced_components"] as Record<
      string,
      ComponentAsDict
    >;
    const result: Record<string, ComponentBase> = {};

    for (const [componentId, componentDict] of Object.entries(refs)) {
      const ctx = new DeserializationContext(this.plugins);
      result[componentId] = ctx.loadConfigDict(
        componentDict,
        opts.componentsRegistry,
      );
    }

    return result;
  }

  /** Deserialize a component from a JSON string */
  fromJson(
    json: string,
    options?: {
      componentsRegistry?: ComponentsRegistry;
      importOnlyReferencedComponents?: boolean;
    },
  ): ComponentBase | Record<string, ComponentBase> {
    return this.fromDict(JSON.parse(json) as ComponentAsDict, options);
  }

  /** Deserialize a component from a YAML string */
  fromYaml(
    yamlStr: string,
    options?: {
      componentsRegistry?: ComponentsRegistry;
      importOnlyReferencedComponents?: boolean;
    },
  ): ComponentBase | Record<string, ComponentBase> {
    return this.fromDict(YAML.parse(yamlStr) as ComponentAsDict, options);
  }

  /** Check that all $component_ref references can be resolved */
  private checkMissingReferences(
    data: ComponentAsDict,
    registry?: ComponentsRegistry,
  ): void {
    const [usedRefs, definedRefs] =
      this.recursivelyGetAllReferences(data);
    const registryIds = new Set(registry?.keys() ?? []);
    const allDefined = new Set([...definedRefs, ...registryIds]);

    const missing: string[] = [];
    for (const ref of usedRefs) {
      if (!allDefined.has(ref)) {
        missing.push(ref);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        "Missing component references that should be passed in the " +
          `components registry: ${missing.sort().join(", ")}`,
      );
    }
  }

  /** Recursively collect all $component_ref uses and $referenced_components definitions */
  private recursivelyGetAllReferences(
    value: unknown,
  ): [Set<string>, Set<string>] {
    const usedRefs = new Set<string>();
    const definedRefs = new Set<string>();
    const visited = new Set<unknown>();
    const stack: unknown[] = [value];

    while (stack.length > 0) {
      const current = stack.pop();
      if (visited.has(current)) continue;
      if (typeof current === "object" && current !== null) {
        visited.add(current);
      }

      if (typeof current === "object" && current !== null && !Array.isArray(current)) {
        const dict = current as Record<string, unknown>;
        if ("$component_ref" in dict) {
          usedRefs.add(dict["$component_ref"] as string);
        }
        if ("$referenced_components" in dict) {
          const refs = dict["$referenced_components"];
          if (typeof refs === "object" && refs !== null) {
            for (const key of Object.keys(refs as Record<string, unknown>)) {
              definedRefs.add(key);
            }
          }
        }
        for (const v of Object.values(dict)) {
          if (typeof v === "object" && v !== null) {
            stack.push(v);
          }
        }
      } else if (Array.isArray(current)) {
        for (const item of current) {
          if (typeof item === "object" && item !== null) {
            stack.push(item);
          }
        }
      }
    }

    return [usedRefs, definedRefs];
  }
}
