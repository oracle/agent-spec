import { resolveMastraDatastore } from "./datastores.js";
import {
  loadMastraRuntimeExport,
  loadMastraRuntimeModule,
} from "./runtime.js";
import type {
  AgentSpecMastraDatastore,
  MastraDatastoreTarget,
  MastraDatastoreTargetOptions,
  MastraRuntimeModuleLoader,
} from "./types.js";

export type MastraStoreConstructor<
  TStore = unknown,
  TConfig = Record<string, unknown>,
> = new (config: TConfig) => TStore;

export type MastraStoreRuntime<TStore = unknown> = {
  Store?: MastraStoreConstructor<TStore>;
  moduleLoader?: MastraRuntimeModuleLoader;
};

export type MastraAppStorageConfig<TStore> = {
  storage: TStore;
};

export type MastraMemoryStorageConfig<TStore> = {
  storage: TStore;
};

export type MastraStorageBundle<TStore = unknown> = {
  target: MastraDatastoreTarget;
  storage: TStore;
  mastraConfig: MastraAppStorageConfig<TStore>;
  memoryConfig: MastraMemoryStorageConfig<TStore>;
};

export const constructMastraDatastore = <TStore = unknown>(
  target: MastraDatastoreTarget,
  runtime: MastraStoreRuntime<TStore> = {},
): TStore => {
  const Store =
    runtime.Store ??
    loadMastraRuntimeExport<MastraStoreConstructor<TStore>>(
      runtime.moduleLoader ?? loadMastraRuntimeModule,
      target.packageName,
      target.exportName,
    );

  return new Store(target.config);
};

export const createMastraAppStorageConfig = <TStore>(
  storage: TStore,
): MastraAppStorageConfig<TStore> => ({ storage });

export const createMastraMemoryStorageConfig = <TStore>(
  storage: TStore,
): MastraMemoryStorageConfig<TStore> => ({ storage });

export function createMastraStorageBundle<TStore = unknown>(
  datastore: AgentSpecMastraDatastore,
  runtime: MastraStoreRuntime<TStore>,
  options?: MastraDatastoreTargetOptions,
): MastraStorageBundle<TStore>;

export function createMastraStorageBundle<TStore = unknown>(
  datastore: AgentSpecMastraDatastore,
  options?: MastraDatastoreTargetOptions,
): MastraStorageBundle<TStore>;

export function createMastraStorageBundle<TStore = unknown>(
  datastore: AgentSpecMastraDatastore,
  runtimeOrOptions: MastraStoreRuntime<TStore> | MastraDatastoreTargetOptions = {},
  maybeOptions?: MastraDatastoreTargetOptions,
): MastraStorageBundle<TStore> {
  const { runtime, options } = parseStorageBundleArgs(
    runtimeOrOptions,
    maybeOptions,
  );
  const target = resolveMastraDatastore(datastore, options);
  const storage = constructMastraDatastore(target, runtime);

  return {
    target,
    storage,
    mastraConfig: createMastraAppStorageConfig(storage),
    memoryConfig: createMastraMemoryStorageConfig(storage),
  };
}

const parseStorageBundleArgs = <TStore>(
  runtimeOrOptions: MastraStoreRuntime<TStore> | MastraDatastoreTargetOptions,
  maybeOptions: MastraDatastoreTargetOptions | undefined,
): {
  runtime: MastraStoreRuntime<TStore>;
  options: MastraDatastoreTargetOptions;
} => {
  if (maybeOptions !== undefined) {
    return {
      runtime: runtimeOrOptions as MastraStoreRuntime<TStore>,
      options: maybeOptions,
    };
  }

  if (isMastraStoreRuntime(runtimeOrOptions)) {
    return {
      runtime: runtimeOrOptions,
      options: {},
    };
  }

  return {
    runtime: {},
    options: runtimeOrOptions,
  };
};

const isMastraStoreRuntime = <TStore>(
  value: MastraStoreRuntime<TStore> | MastraDatastoreTargetOptions,
): value is MastraStoreRuntime<TStore> =>
  "Store" in value || "moduleLoader" in value;
