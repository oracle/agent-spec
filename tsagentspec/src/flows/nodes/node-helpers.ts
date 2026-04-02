/**
 * Shared helpers for flow node types.
 */
import { DEFAULT_NEXT_BRANCH } from "../node.js";

/**
 * Extract branch names from EndNodes in a subflow's nodes array.
 * @param defaultBranches Branches to return if no EndNodes are found.
 */
export function getEndNodeBranches(
  subflow: Record<string, unknown>,
  defaultBranches: string[] = [DEFAULT_NEXT_BRANCH],
): string[] {
  const nodes = subflow["nodes"] as Record<string, unknown>[] | undefined;
  if (!nodes) return defaultBranches;
  const branches = new Set<string>();
  for (const node of nodes) {
    if (node["componentType"] === "EndNode") {
      const branchName =
        (node["branchName"] as string) ?? DEFAULT_NEXT_BRANCH;
      branches.add(branchName);
    }
  }
  return branches.size > 0 ? [...branches].sort() : defaultBranches;
}
