/**
 * Template placeholder extraction from strings and nested objects.
 */
import type { Property } from "./property.js";

/** Regex matching {{variable_name}} placeholders */
export const TEMPLATE_PLACEHOLDER_REGEXP = /\{\{\s*(\w+)\s*\}\}/g;

/** Extract placeholder names from a string */
export function getPlaceholdersFromString(str: string): string[] {
  const matches = new Set<string>();
  let match: RegExpExecArray | null;
  const re = new RegExp(TEMPLATE_PLACEHOLDER_REGEXP.source, "g");
  while ((match = re.exec(str)) !== null) {
    if (match[1]) matches.add(match[1]);
  }
  return [...matches];
}

/** Recursively extract placeholder names from any JSON-serializable object */
export function getPlaceholdersFromJsonObject(obj: unknown): string[] {
  if (typeof obj === "string") {
    return getPlaceholdersFromString(obj);
  }
  if (obj instanceof Uint8Array) {
    return getPlaceholdersFromJsonObject(obj.toString());
  }
  if (Array.isArray(obj)) {
    const all = new Set<string>();
    for (const item of obj) {
      for (const p of getPlaceholdersFromJsonObject(item)) {
        all.add(p);
      }
    }
    return [...all];
  }
  if (typeof obj === "object" && obj !== null) {
    const dict = obj as Record<string, unknown>;
    const keyPlaceholders = getPlaceholdersFromJsonObject(Object.keys(dict));
    const valuePlaceholders = getPlaceholdersFromJsonObject(
      Object.values(dict),
    );
    return [...new Set([...keyPlaceholders, ...valuePlaceholders])];
  }
  return [];
}

/** Extract Property[] for each unique placeholder found in a JSON-serializable object */
export function getPlaceholderPropertiesFromJsonObject(
  obj: unknown,
): Property[] {
  const placeholders = getPlaceholdersFromJsonObject(obj);
  return placeholders.map((name) => ({
    jsonSchema: { title: name, type: "string" },
    title: name,
    description: undefined,
    default: undefined,
    type: "string",
  }));
}
