import { describe, expect, it } from "vitest";
import {
  createInMemoryCollectionDatastore,
} from "../../../src/index.js";
import {
  constructMastraDatastore,
  createMastraAppStorageConfig,
  createMastraMemoryStorageConfig,
  createMastraStorageBundle,
  MissingMastraRuntimeDependencyError,
  resolveInMemoryDatastore,
} from "../../../src/adapters/mastra/index.js";

class FakeStore {
  readonly config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }
}

describe("Mastra datastore factory", () => {
  it("constructs a datastore with the resolved default Mastra store export", () => {
    class FakeInMemoryStore {
      readonly config: Record<string, unknown>;

      constructor(config: Record<string, unknown>) {
        this.config = config;
      }
    }

    const datastore = createInMemoryCollectionDatastore({
      id: "memory-ds",
      name: "memory",
      datastoreSchema: {},
    });
    const target = resolveInMemoryDatastore(datastore);

    const store = constructMastraDatastore(target, {
      moduleLoader: (packageName) => {
        expect(packageName).toBe("@mastra/core/storage");
        return { InMemoryStore: FakeInMemoryStore };
      },
    });

    expect(store).toBeInstanceOf(FakeInMemoryStore);
    expect(store.config).toEqual({ id: "memory-ds" });
  });

  it("fails explicitly when the resolved store package is unavailable", () => {
    const datastore = createInMemoryCollectionDatastore({
      id: "memory-ds",
      name: "memory",
      datastoreSchema: {},
    });
    const target = resolveInMemoryDatastore(datastore);

    expect(() =>
      constructMastraDatastore(target, {
        moduleLoader: () => {
          throw new Error("missing module");
        },
      }),
    ).toThrow(
      MissingMastraRuntimeDependencyError,
    );
  });

  it("creates Mastra app and Memory storage configs from a store", () => {
    const store = new FakeStore({ id: "memory-store" });

    expect(createMastraAppStorageConfig(store)).toEqual({ storage: store });
    expect(createMastraMemoryStorageConfig(store)).toEqual({ storage: store });
  });

  it("creates a storage bundle with implicit runtime module binding", () => {
    const datastore = createInMemoryCollectionDatastore({
      id: "memory-ds",
      name: "memory",
      datastoreSchema: {},
    });

    const bundle = createMastraStorageBundle(datastore, {
      moduleLoader: () => ({ InMemoryStore: FakeStore }),
    });

    expect(bundle.target.provider).toBe("in-memory");
    expect(bundle.storage).toBeInstanceOf(FakeStore);
    expect(bundle.mastraConfig).toEqual({ storage: bundle.storage });
    expect(bundle.memoryConfig).toEqual({ storage: bundle.storage });
  });
});
