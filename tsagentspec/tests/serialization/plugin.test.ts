import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  type ComponentSerializationPlugin,
  type ComponentDeserializationPlugin,
  CURRENT_VERSION,
} from "../../src/index.js";
import type { SerializedFields, SerializedDict } from "../../src/serialization/types.js";
import type { SerializationContext } from "../../src/serialization/serialization-context.js";
import type { DeserializationContext } from "../../src/serialization/deserialization-context.js";
import type { ComponentBase } from "../../src/component.js";

// A custom component type for testing plugins
interface CustomComponent extends ComponentBase {
  componentType: "CustomWidget";
  widgetColor: string;
  widgetSize: number;
}

class CustomSerializationPlugin implements ComponentSerializationPlugin {
  readonly pluginName = "CustomWidgetPlugin";
  readonly pluginVersion = "1.0.0";

  supportedComponentTypes(): string[] {
    return ["CustomWidget"];
  }

  serialize(
    component: ComponentBase,
    _context: SerializationContext,
  ): SerializedFields {
    const custom = component as unknown as CustomComponent;
    return {
      id: custom.id,
      name: custom.name,
      description: custom.description ?? null,
      metadata: custom.metadata,
      widget_color: custom.widgetColor,
      widget_size: custom.widgetSize,
    };
  }
}

class CustomDeserializationPlugin implements ComponentDeserializationPlugin {
  readonly pluginName = "CustomWidgetPlugin";
  readonly pluginVersion = "1.0.0";

  supportedComponentTypes(): string[] {
    return ["CustomWidget"];
  }

  deserialize(
    data: SerializedDict,
    _context: DeserializationContext,
  ): ComponentBase {
    return {
      id: data["id"] as string,
      name: data["name"] as string,
      description: data["description"] as string | undefined,
      metadata: (data["metadata"] as Record<string, unknown>) ?? {},
      componentType: "CustomWidget",
      widgetColor: data["widget_color"] as string,
      widgetSize: data["widget_size"] as number,
    } as unknown as ComponentBase;
  }
}

describe("Custom serialization plugins", () => {
  it("should serialize a custom component type", () => {
    const serializer = new AgentSpecSerializer([
      new CustomSerializationPlugin(),
    ]);

    const widget: CustomComponent = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "my-widget",
      description: "A custom widget",
      metadata: {},
      componentType: "CustomWidget",
      widgetColor: "red",
      widgetSize: 42,
    };

    const json = serializer.toJson(widget as any) as string;
    const dict = JSON.parse(json);
    expect(dict["component_type"]).toBe("CustomWidget");
    expect(dict["widget_color"]).toBe("red");
    expect(dict["widget_size"]).toBe(42);
    // Non-builtin components should get plugin metadata
    expect(dict["component_plugin_name"]).toBe("CustomWidgetPlugin");
    expect(dict["component_plugin_version"]).toBe("1.0.0");
  });

  it("should deserialize a custom component type", () => {
    const deserializer = new AgentSpecDeserializer([
      new CustomDeserializationPlugin(),
    ]);

    const dict = {
      agentspec_version: CURRENT_VERSION,
      component_type: "CustomWidget",
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "my-widget",
      description: "A custom widget",
      metadata: {},
      widget_color: "blue",
      widget_size: 99,
    };

    const result = deserializer.fromJson(JSON.stringify(dict)) as Record<string, unknown>;
    expect(result["componentType"]).toBe("CustomWidget");
    expect(result["name"]).toBe("my-widget");
    expect(result["widgetColor"]).toBe("blue");
    expect(result["widgetSize"]).toBe(99);
  });

  it("should round-trip a custom component with plugins", () => {
    const serializer = new AgentSpecSerializer([
      new CustomSerializationPlugin(),
    ]);
    const deserializer = new AgentSpecDeserializer([
      new CustomDeserializationPlugin(),
    ]);

    const widget: CustomComponent = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "round-trip-widget",
      metadata: {},
      componentType: "CustomWidget",
      widgetColor: "green",
      widgetSize: 7,
    } as any;

    const json = serializer.toJson(widget as any) as string;
    const result = deserializer.fromJson(json) as Record<string, unknown>;
    expect(result["componentType"]).toBe("CustomWidget");
    expect(result["name"]).toBe("round-trip-widget");
    expect(result["widgetColor"]).toBe("green");
    expect(result["widgetSize"]).toBe(7);
  });

  it("should throw if multiple plugins handle the same component type", () => {
    expect(
      () =>
        new AgentSpecSerializer([
          new CustomSerializationPlugin(),
          new CustomSerializationPlugin(),
        ]),
    ).toThrow("Multiple plugins");
  });
});
