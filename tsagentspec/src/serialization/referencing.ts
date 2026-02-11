/**
 * Component reference system.
 *
 * Computes the referencing structure for shared components in a component tree.
 * When a component is referenced from multiple places, it is serialized once and
 * other locations use $component_ref pointers.
 */
import type { ComponentBase } from "../component.js";

/** Check if a value is a component (has id, name, componentType) */
function isComponent(value: unknown): value is ComponentBase {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj["id"] === "string" &&
    typeof obj["name"] === "string" &&
    typeof obj["componentType"] === "string"
  );
}

/** Extract Component children from a field value (handles arrays, single components, dicts) */
export function getChildrenFromFieldValue(
  fieldValue: unknown,
): ComponentBase[] {
  if (isComponent(fieldValue)) {
    return [fieldValue];
  }
  if (Array.isArray(fieldValue)) {
    const children: ComponentBase[] = [];
    for (const item of fieldValue) {
      children.push(...getChildrenFromFieldValue(item));
    }
    return children;
  }
  if (typeof fieldValue === "object" && fieldValue !== null && !isComponent(fieldValue)) {
    const children: ComponentBase[] = [];
    for (const v of Object.values(fieldValue as Record<string, unknown>)) {
      children.push(...getChildrenFromFieldValue(v));
    }
    return children;
  }
  return [];
}

/** Get all direct Component children of a component */
export function getAllDirectChildren(
  component: ComponentBase,
): Record<string, string[]> {
  const children: Record<string, string[]> = {};
  const queue: ComponentBase[] = [component];

  while (queue.length > 0) {
    const current = queue.pop()!;
    if (current.id in children) continue;

    const directChildren: string[] = [];
    const obj = current as unknown as Record<string, unknown>;
    for (const [key, value] of Object.entries(obj)) {
      if (key === "id" || key === "componentType") continue;
      const innerChildren = getChildrenFromFieldValue(value);
      for (const child of innerChildren) {
        directChildren.push(child.id);
        queue.push(child);
      }
    }
    children[current.id] = directChildren;
  }

  return children;
}

/**
 * Compute the referencing structure of a component tree.
 *
 * Returns a mapping of component IDs to the ID of the parent component
 * that should contain them in its $referenced_components section.
 *
 * This uses DFS to find the highest component in the DAG that references
 * each multiply-referenced component.
 */
export function computeReferencingStructure(
  component: ComponentBase,
): Record<string, string> {
  const children = getAllDirectChildren(component);

  // For every node_id, stores the reference level assignments for all
  // reachable child components from that node's perspective.
  const referenceLevelsAtNode: Record<
    string,
    Record<string, string | [null, string]>
  > = {};

  function innerComputeReferences(nodeId: string): void {
    if (nodeId in referenceLevelsAtNode) return;

    const nodeChildren = children[nodeId] ?? [];
    for (const childNode of nodeChildren) {
      innerComputeReferences(childNode);
    }

    const currentReferenceLevels: Record<string, string | [null, string]> = {};

    // Count occurrences of each child
    const childCounts = new Map<string, number>();
    for (const childId of nodeChildren) {
      childCounts.set(childId, (childCounts.get(childId) ?? 0) + 1);
    }

    for (const [childNodeId, childUsageCount] of childCounts.entries()) {
      // Component used multiple times directly by this node
      if (childUsageCount > 1 || childNodeId in currentReferenceLevels) {
        currentReferenceLevels[childNodeId] = nodeId;
      } else {
        // Mark as potentially not needing a reference
        currentReferenceLevels[childNodeId] = [null, nodeId];
      }

      // Merge reference levels from the child's subtree
      const childRefLevels = referenceLevelsAtNode[childNodeId] ?? {};
      for (const [referencedByChild, refLevelAtChild] of Object.entries(
        childRefLevels,
      )) {
        if (!(referencedByChild in currentReferenceLevels)) {
          currentReferenceLevels[referencedByChild] = refLevelAtChild;
        } else {
          // If two children reference the same component differently,
          // the parent takes the reference
          const existing = currentReferenceLevels[referencedByChild];
          const existingStr = Array.isArray(existing)
            ? JSON.stringify(existing)
            : existing;
          const newStr = Array.isArray(refLevelAtChild)
            ? JSON.stringify(refLevelAtChild)
            : refLevelAtChild;
          if (existingStr !== newStr) {
            currentReferenceLevels[referencedByChild] = nodeId;
          }
        }
      }
    }

    referenceLevelsAtNode[nodeId] = currentReferenceLevels;
  }

  innerComputeReferences(component.id);

  const referenceLevelsAtRoot = referenceLevelsAtNode[component.id] ?? {};

  // Only keep entries where the level is a string (actual reference needed),
  // not [null, parentId] tuples (no reference needed)
  const resolved: Record<string, string> = {};
  for (const [nid, level] of Object.entries(referenceLevelsAtRoot)) {
    if (typeof level === "string") {
      resolved[nid] = level;
    }
  }
  return resolved;
}
