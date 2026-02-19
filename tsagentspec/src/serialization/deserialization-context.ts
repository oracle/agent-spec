/**
 * DeserializationContext - handles the recursive deserialization of components.
 *
 * Manages snake_case -> camelCase conversion, $component_ref resolution,
 * $referenced_components merging, and plugin dispatch.
 */
import type { AgentSpecVersion } from "../versioning.js";
import {
  CURRENT_VERSION,
  PRERELEASE_AGENTSPEC_VERSIONS,
} from "../versioning.js";
import type { ComponentBase } from "../component.js";
import type { ComponentDeserializationPlugin } from "./deserialization-plugin.js";
import {
  DANGEROUS_KEYS,
  DeserializationInProgressMarker,
  getProtocolKeys,
  isComponentRef,
  isSerializedComponent,
  type ComponentsRegistry,
  type SerializedDict,
} from "./types.js";

/** Legacy field name for backwards compat */
const LEGACY_VERSION_FIELD_NAME = "air_version";

export class DeserializationContext {
  private componentTypesToPlugins: Map<
    string,
    ComponentDeserializationPlugin
  >;
  agentspecVersion: AgentSpecVersion | undefined;
  camelCase: boolean;
  loadedReferences: Map<
    string,
    ComponentBase | DeserializationInProgressMarker
  > = new Map();
  referencedComponents: Map<string, SerializedDict> = new Map();

  constructor(
    plugins: ComponentDeserializationPlugin[],
    sourceVersion?: AgentSpecVersion,
    camelCase?: boolean,
  ) {
    this.agentspecVersion = sourceVersion;
    this.camelCase = camelCase ?? false;
    this.componentTypesToPlugins =
      this.buildComponentTypesToPlugins(plugins);
  }

  private buildComponentTypesToPlugins(
    plugins: ComponentDeserializationPlugin[],
  ): Map<string, ComponentDeserializationPlugin> {
    const map = new Map<string, ComponentDeserializationPlugin>();
    for (const plugin of plugins) {
      for (const ct of plugin.supportedComponentTypes()) {
        if (map.has(ct)) {
          throw new Error(
            `Multiple plugins handle deserialization of component type "${ct}". ` +
              "Remove duplicate plugins.",
          );
        }
        map.set(ct, plugin);
      }
    }
    return map;
  }

  /** Get the component_type from a serialized dict */
  getComponentType(content: SerializedDict): string {
    const keys = getProtocolKeys(this.camelCase);
    const dict = content as Record<string, unknown>;
    const componentType = dict[keys.componentType];
    if (componentType === undefined || componentType === null) {
      throw new Error(
        "Cannot deserialize: missing 'component_type' field in " +
          JSON.stringify(content).slice(0, 200),
      );
    }
    if (typeof componentType !== "string") {
      throw new Error("component_type is not a string");
    }
    return componentType;
  }

  /** Resolve a $component_ref reference */
  loadReference(referenceId: string): ComponentBase {
    if (!this.loadedReferences.has(referenceId)) {
      // Mark as in-progress to detect circular dependencies
      this.loadedReferences.set(
        referenceId,
        new DeserializationInProgressMarker(),
      );

      const refContent = this.referencedComponents.get(referenceId);
      if (!refContent) {
        throw new Error(`Missing reference for ID: ${referenceId}`);
      }
      const loaded = this.loadComponentFromDict(refContent);
      this.loadedReferences.set(referenceId, loaded);
    }

    const loaded = this.loadedReferences.get(referenceId);
    if (loaded instanceof DeserializationInProgressMarker) {
      throw new Error(
        `Circular dependency during deserialization of object with id: '${referenceId}'`,
      );
    }
    return loaded!;
  }

  /** Load a single field value, handling component refs and nested structures */
  loadField(value: unknown): unknown {
    if (value === null || value === undefined) {
      return undefined;
    }

    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      // Handle $component_ref
      if (isComponentRef(value)) {
        return this.loadReference(value["$component_ref"]);
      }
      // Handle nested component (has component_type or componentType)
      if (isSerializedComponent(value)) {
        return this.loadComponentFromDict(value);
      }
      // Plain objects - preserve keys as-is (user data), recursively load values
      const dict = value as Record<string, unknown>;
      const result: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(dict)) {
        if (DANGEROUS_KEYS.has(k)) continue;
        result[k] = this.loadField(v);
      }
      return result;
    }

    if (Array.isArray(value)) {
      return value.map((item) => this.loadField(item));
    }

    // Primitives
    return value;
  }

  /** Deserialize a full component from a dict */
  loadComponentFromDict(content: SerializedDict): ComponentBase {
    const dict = content as Record<string, unknown>;

    // Merge any $referenced_components into our registry
    if ("$referenced_components" in dict) {
      const newRefs = dict["$referenced_components"] as Record<
        string,
        SerializedDict
      >;
      for (const [id, refContent] of Object.entries(newRefs)) {
        if (this.referencedComponents.has(id)) {
          throw new Error(
            `Component "${id}" appears multiple times in referenced components`,
          );
        }
        this.referencedComponents.set(id, refContent);
      }
    }

    // Handle $component_ref at the top level
    if (isComponentRef(content)) {
      return this.loadReference(content["$component_ref"]);
    }

    const componentType = this.getComponentType(content);
    const plugin = this.componentTypesToPlugins.get(componentType);
    if (!plugin) {
      throw new Error(
        `No plugin to deserialize component type "${componentType}"`,
      );
    }

    return plugin.deserialize(content, this);
  }

  /** Load a component registry from external sources */
  loadComponentRegistry(
    registry: ComponentsRegistry | undefined,
  ): void {
    if (!registry) return;
    for (const [id, component] of registry.entries()) {
      this.loadedReferences.set(id, component);
    }
  }

  /** Top-level entry point for deserialization */
  loadConfigDict(
    content: SerializedDict,
    componentsRegistry?: ComponentsRegistry,
  ): ComponentBase {
    const dict = content as Record<string, unknown>;
    const keys = getProtocolKeys(this.camelCase);

    // Extract agentspec_version
    const versionStr =
      (dict[keys.agentspecVersion] as string | undefined) ??
      (dict[LEGACY_VERSION_FIELD_NAME] as string | undefined);

    if (!versionStr) {
      this.agentspecVersion = CURRENT_VERSION;
    } else {
      if (PRERELEASE_AGENTSPEC_VERSIONS.has(versionStr)) {
        this.agentspecVersion = "25.4.1" as AgentSpecVersion;
      } else {
        this.agentspecVersion = versionStr as AgentSpecVersion;
      }
    }

    this.loadComponentRegistry(componentsRegistry);
    return this.loadComponentFromDict(content);
  }
}
