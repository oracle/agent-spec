export class MastraAdapterError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MastraAdapterError";
  }
}

export class UnsupportedMastraDatastoreError extends MastraAdapterError {
  constructor(componentType: string) {
    super(`Unsupported Agent Spec datastore for Mastra adapter: ${componentType}`);
    this.name = "UnsupportedMastraDatastoreError";
  }
}

export class MissingMastraRuntimeDependencyError extends MastraAdapterError {
  constructor(packageName: string, exportName: string) {
    super(
      `Mastra runtime dependency is required: install '${packageName}' with export '${exportName}', or pass a custom runtime to the Mastra adapter.`,
    );
    this.name = "MissingMastraRuntimeDependencyError";
  }
}

export class UnsupportedMastraModelError extends MastraAdapterError {
  constructor(componentType: string) {
    super(`Unsupported Agent Spec LLM config for Mastra adapter: ${componentType}`);
    this.name = "UnsupportedMastraModelError";
  }
}

export class UnsupportedMastraToolError extends MastraAdapterError {
  constructor(componentType: string) {
    super(`Unsupported Agent Spec tool for Mastra adapter: ${componentType}`);
    this.name = "UnsupportedMastraToolError";
  }
}

export class MissingMastraToolExecutorError extends MastraAdapterError {
  constructor(toolName: string) {
    super(
      `ServerTool '${toolName}' requires an executor in the Mastra toolRegistry.`,
    );
    this.name = "MissingMastraToolExecutorError";
  }
}

export class DuplicateMastraToolNameError extends MastraAdapterError {
  constructor(toolName: string) {
    super(`Duplicate Agent Spec tool name cannot be mapped to Mastra: ${toolName}`);
    this.name = "DuplicateMastraToolNameError";
  }
}

export class UnsupportedMastraAgentFeatureError extends MastraAdapterError {
  constructor(feature: string) {
    super(`Unsupported Agent Spec agent feature for Mastra adapter: ${feature}`);
    this.name = "UnsupportedMastraAgentFeatureError";
  }
}

export class InvalidMastraAgentSpecError extends MastraAdapterError {
  constructor(message: string) {
    super(message);
    this.name = "InvalidMastraAgentSpecError";
  }
}

export class UnsupportedMastraFlowNodeError extends MastraAdapterError {
  constructor(componentType: string) {
    super(`Unsupported Agent Spec flow node for Mastra adapter: ${componentType}`);
    this.name = "UnsupportedMastraFlowNodeError";
  }
}

export class UnsupportedMastraFlowShapeError extends MastraAdapterError {
  constructor(message: string) {
    super(message);
    this.name = "UnsupportedMastraFlowShapeError";
  }
}

export class MissingMastraFlowNodeExecutorError extends MastraAdapterError {
  constructor(nodeName: string) {
    super(`Flow node '${nodeName}' requires an executor for Mastra conversion.`);
    this.name = "MissingMastraFlowNodeExecutorError";
  }
}

export class UnsupportedMastraExportError extends MastraAdapterError {
  constructor(message: string) {
    super(message);
    this.name = "UnsupportedMastraExportError";
  }
}
