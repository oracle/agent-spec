# OpenAI Agents Runtime for Agent Spec Conformance

This runtime integrates the OpenAI Agents Spec Adapter with the AgentSpec Conformance Test Suite (CTS).

It loads Agent Spec configurations using the `openai-agentspec-adapter` and runs them via the OpenAI Agents Python SDK where supported.

Notes and limitations:
- Supported components: Agent, Flow (generated Python workflow).
- Supported tools: ServerTool, RemoteTool.
- Not supported: ClientTool interactive pause/resume. Configurations containing ClientTool on Agents or Flows will raise a clear error.
- LLMs: Agent Spec `VllmConfig` is mapped to OpenAI-compatible models using the provided `url` (e.g., CTS local deterministic LLM at `http://localhost:5006`).

Run the CTS against this runtime:

- From repo root, set the runtime and run pytest in `conformance_test_suite`:

  RUNTIME_CLASS_IMPORT_PATH=openairuntime.OpenAIAgentSpecLoader pytest conformance_test_suite/tests

Environment:
- Requires `openai-agents` and `openai` installed (already required by the adapter).
- CTS brings its own local deterministic LLM server for `VllmConfig` scenarios.

## Install

```bash
sh install-dev.sh
```
