import { describe, it, expect } from "vitest";
import {
  AgentSpecVersion,
  CURRENT_VERSION,
  AGENTSPEC_VERSION_FIELD_NAME,
  LEGACY_AGENTSPEC_VERSIONS,
  versionLt,
  versionGte,
  versionMax,
} from "../src/index.js";

describe("AgentSpecVersion", () => {
  it("should define all known versions", () => {
    expect(AgentSpecVersion.V25_3_0).toBe("25.3.0");
    expect(AgentSpecVersion.V25_3_1).toBe("25.3.1");
    expect(AgentSpecVersion.V25_4_0).toBe("25.4.0");
    expect(AgentSpecVersion.V25_4_1).toBe("25.4.1");
    expect(AgentSpecVersion.V25_4_2).toBe("25.4.2");
    expect(AgentSpecVersion.V26_1_0).toBe("26.1.0");
    expect(AgentSpecVersion.V26_2_0).toBe("26.2.0");
  });

  it("should set CURRENT_VERSION to the latest version", () => {
    expect(CURRENT_VERSION).toBe("26.2.0");
    expect(CURRENT_VERSION).toBe(AgentSpecVersion.V26_2_0);
  });

  it("should define the version field name", () => {
    expect(AGENTSPEC_VERSION_FIELD_NAME).toBe("agentspec_version");
  });

  it("should define legacy versions", () => {
    expect(LEGACY_AGENTSPEC_VERSIONS.has("25.3.0")).toBe(true);
    expect(LEGACY_AGENTSPEC_VERSIONS.has("25.3.1")).toBe(true);
    expect(LEGACY_AGENTSPEC_VERSIONS.has("25.4.0")).toBe(true);
    expect(LEGACY_AGENTSPEC_VERSIONS.has("25.4.1")).toBe(false);
    expect(LEGACY_AGENTSPEC_VERSIONS.has("26.2.0")).toBe(false);
  });
});

describe("versionLt", () => {
  it("should return true when a < b", () => {
    expect(versionLt(AgentSpecVersion.V25_3_0, AgentSpecVersion.V25_4_0)).toBe(
      true,
    );
    expect(versionLt(AgentSpecVersion.V25_4_1, AgentSpecVersion.V26_1_0)).toBe(
      true,
    );
    expect(versionLt(AgentSpecVersion.V25_3_0, AgentSpecVersion.V25_3_1)).toBe(
      true,
    );
  });

  it("should return false when a == b", () => {
    expect(versionLt(AgentSpecVersion.V25_4_1, AgentSpecVersion.V25_4_1)).toBe(
      false,
    );
    expect(versionLt(AgentSpecVersion.V26_2_0, AgentSpecVersion.V26_2_0)).toBe(
      false,
    );
  });

  it("should return false when a > b", () => {
    expect(versionLt(AgentSpecVersion.V26_2_0, AgentSpecVersion.V25_3_0)).toBe(
      false,
    );
    expect(versionLt(AgentSpecVersion.V25_4_2, AgentSpecVersion.V25_4_1)).toBe(
      false,
    );
  });

  it("should handle major version differences", () => {
    expect(versionLt(AgentSpecVersion.V25_4_2, AgentSpecVersion.V26_1_0)).toBe(
      true,
    );
    expect(versionLt(AgentSpecVersion.V26_1_0, AgentSpecVersion.V25_4_2)).toBe(
      false,
    );
  });
});

describe("versionGte", () => {
  it("should return true when a >= b", () => {
    expect(
      versionGte(AgentSpecVersion.V25_4_1, AgentSpecVersion.V25_4_1),
    ).toBe(true);
    expect(
      versionGte(AgentSpecVersion.V26_2_0, AgentSpecVersion.V25_3_0),
    ).toBe(true);
  });

  it("should return false when a < b", () => {
    expect(
      versionGte(AgentSpecVersion.V25_3_0, AgentSpecVersion.V26_2_0),
    ).toBe(false);
  });
});

describe("versionMax", () => {
  it("should return the greater version", () => {
    expect(
      versionMax(AgentSpecVersion.V25_3_0, AgentSpecVersion.V26_2_0),
    ).toBe(AgentSpecVersion.V26_2_0);
    expect(
      versionMax(AgentSpecVersion.V26_2_0, AgentSpecVersion.V25_3_0),
    ).toBe(AgentSpecVersion.V26_2_0);
  });

  it("should return either when equal", () => {
    expect(
      versionMax(AgentSpecVersion.V25_4_1, AgentSpecVersion.V25_4_1),
    ).toBe(AgentSpecVersion.V25_4_1);
  });
});
