/**
 * Version tracking for the Oracle Open Agent Specification.
 */

/** All known agent spec versions */
export const AgentSpecVersion = {
  V25_3_0: "25.3.0",
  V25_3_1: "25.3.1",
  V25_4_0: "25.4.0",
  V25_4_1: "25.4.1",
  V25_4_2: "25.4.2",
  V26_1_0: "26.1.0",
  V26_2_0: "26.2.0",
} as const;

export type AgentSpecVersion =
  (typeof AgentSpecVersion)[keyof typeof AgentSpecVersion];

/** The current (latest) agent spec version */
export const CURRENT_VERSION: AgentSpecVersion = AgentSpecVersion.V26_2_0;

/** Field name for the agentspec version in serialized JSON/YAML */
export const AGENTSPEC_VERSION_FIELD_NAME = "agentspec_version";

/** Legacy field name (backwards compat) */
export const LEGACY_VERSION_FIELD_NAME = "air_version";

/** Versions considered legacy */
export const LEGACY_AGENTSPEC_VERSIONS = new Set<string>([
  "25.3.0",
  "25.3.1",
  "25.4.0",
]);

/** Pre-release versions */
export const PRERELEASE_AGENTSPEC_VERSIONS = new Set<string>(["25.4.0"]);

function parseVersion(v: string): number[] {
  return v.split(".").map(Number);
}

/** Returns true if version a is strictly less than version b */
export function versionLt(a: AgentSpecVersion, b: AgentSpecVersion): boolean {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    if (pa[i]! < pb[i]!) return true;
    if (pa[i]! > pb[i]!) return false;
  }
  return false;
}

/** Returns true if version a is greater than or equal to version b */
export function versionGte(a: AgentSpecVersion, b: AgentSpecVersion): boolean {
  return !versionLt(a, b);
}

/** Returns the greater of two versions */
export function versionMax(
  a: AgentSpecVersion,
  b: AgentSpecVersion,
): AgentSpecVersion {
  return versionLt(a, b) ? b : a;
}
