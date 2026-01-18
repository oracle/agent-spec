# Core AI Tools in Oracle Agent Spec Ecosystem


* Framework-agnostic agent definitions
  Agent Spec itself is a declarative configuration language for defining AI agents and workflows (not a single AI model/tool). It lets you describe how an agent should behave, what tools it uses, and how workflows are structured — in a portable, framework-neutral format.

* Runtime execution frameworks
  To actually run agents defined with Agent Spec, you use one of several runtime/agent execution tools:

* WayFlow — Oracle’s reference Agent Spec runtime.

* LangGraph, AutoGen, CrewAI — Community or partner frameworks that can interpret and execute Agent Spec definitions.

* LLM integrations (AI models)
  Agents typically call large language models (LLMs) to generate responses, reason, plan, and act. In the Agent Spec context (especially via the PyAgentSpec SDK), supported models include:

* OCI GenAI (Oracle Cloud’s generative models)

* OpenAI models

* Ollama models
  These are configured via abstraction layers in the SDK, so the agent logic stays compatible regardless of the underlying LLM.

* Oracle Cloud AI Platform tools (often combined with Agent Spec)
  When building real enterprise agents (e.g., via OCI AI Agent Platform), Oracle’s tooling can include:

* Retrieval-Augmented Generation (RAG) — to fetch context from enterprise knowledge bases.

* SQL tools — convert natural language to SQL and run against databases.

* Custom function calling — enables agents to execute arbitrary custom functions or APIs.

* User interaction tooling
  While not part of Agent Spec’s core spec, AG-UI (Agent-User Interaction protocol) can be used alongside Agent Spec to standardize how agents communicate with front-ends and interactive apps.
