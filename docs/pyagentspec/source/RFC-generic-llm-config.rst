:orphan:

==================================
RFC: Generic LLM Configuration
==================================

This RFC proposes making ``LlmConfig`` non-abstract and adding flat,
provider-agnostic fields (``provider``, ``api_provider``, ``api_type``) so
that any LLM connection can be described without requiring a dedicated
subclass per provider.

Summary
-------

Make ``LlmConfig`` a concrete, directly instantiable class by removing its
``abstract=True`` marker and adding three optional string fields --
``provider``, ``api_provider``, and ``api_type`` -- that together describe
the model origin, API host, and wire protocol.  Existing subclasses continue
to work unchanged, freezing these fields where appropriate.

Motivation
----------

The current ``LlmConfig`` hierarchy requires a dedicated subclass for every LLM
provider (``OpenAiConfig``, ``OciGenAiConfig``, ``OllamaConfig``, etc.).  This
design creates several practical problems:

1. **Every new provider requires a spec change.**
   Adding support for a provider today means creating a new ``LlmConfig``
   subclass, updating every framework adapter, and cutting a new spec version.
   This does not scale as the provider landscape grows.

2. **Significant duplication across configs.**
   Most existing ``LlmConfig`` subclasses share the same core fields
   (``model_id``, ``api_key``, an endpoint URL) but repeat them independently.
   For example, ``OpenAiConfig``, ``OpenAiCompatibleConfig``, ``VllmConfig``,
   and ``OllamaConfig`` all declare ``model_id`` and ``api_key``.  The same
   duplication propagates into every framework adapter, which must handle each
   subclass individually despite nearly identical logic.

3. **"OpenAI Compatible" is not universal.**
   Providers such as Anthropic, AWS Bedrock, Azure OpenAI, and Google Vertex AI
   each have their own API surface, authentication mechanisms, and endpoint
   conventions.  Forcing them through ``OpenAiCompatibleConfig`` loses important
   provider-specific details.

4. **Provider identity is tangled with wire protocol.**
   There is no way to express "OCI GenAI service accessed via the OpenAI chat
   completions protocol" because the config class itself implies the protocol.
   Separating the *who* (provider) from the *how* (protocol) enables more
   flexible deployments.

Proposal
--------

Instead of introducing a new ``GenericLlmConfig`` component, the proposal
makes ``LlmConfig`` itself non-abstract and adds three optional string fields
directly to it.  This avoids fragmenting the config hierarchy and keeps the
surface area small.

``LlmConfig`` changes
^^^^^^^^^^^^^^^^^^^^^

Remove the ``abstract=True`` marker so that ``LlmConfig`` can be instantiated
directly, and add the following fields:

.. code-block:: python

   class LlmConfig(Component):  # no longer abstract
       """A generic, provider-agnostic LLM configuration."""

       model_id: str
       """Primary model identifier."""

       provider: Optional[str] = None
       """Model provider (e.g. "meta", "openai", "anthropic", "cohere")."""

       api_provider: Optional[str] = None
       """API provider (e.g. "oci", "openai", "vertex_ai", "aws_bedrock",
       "azure_openai")."""

       api_type: Optional[str] = None
       """API protocol to use (e.g. "chat_completions", "responses")."""

       default_generation_parameters: Optional[LlmGenerationConfig] = None
       """Parameters used for the generation call of this LLM."""

The three new fields are **independent axes**:

- ``provider`` identifies **who made the model** (Meta, OpenAI, Anthropic,
  Cohere, ...).
- ``api_provider`` identifies **who serves the API** (OCI, OpenAI, Vertex AI,
  AWS Bedrock, Azure OpenAI, ...).
- ``api_type`` identifies **the wire protocol** (``chat_completions``,
  ``responses``, ...).

All three are optional strings.  The spec documents well-known values for
each (see `Well-known values`_), but users are free to use any string to
support new models, providers, and APIs without waiting for a spec update.

YAML schema
^^^^^^^^^^^

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   spec:
     model_id: <string>                    # required
     provider: <string>                    # optional — model provider
     api_provider: <string>                # optional — API provider
     api_type: <string>                    # optional — wire protocol
     default_generation_parameters:        # optional
       ...

Existing subclass integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Existing ``LlmConfig`` subclasses freeze the new fields where the value is
known a priori.  Frozen fields are excluded from serialization for brevity.

.. code-block:: python

   class OpenAiConfig(LlmConfig):
       provider: str = "openai"
       api_provider: str = "openai"
       # api_type already exists on this class
       ...

   class OciGenAiConfig(LlmConfig):
       # provider already exists on this class (ModelProvider enum)
       api_provider: str = "oci"
       # api_type already exists on this class (OciAPIType enum)
       ...

   class OpenAiCompatibleConfig(LlmConfig):
       # provider and api_provider are unknown — left as None
       # api_type already exists on this class
       ...

The following table summarizes how each existing subclass maps to the new
fields:

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 20

   * - Existing config
     - ``provider``
     - ``api_provider``
     - ``api_type``
   * - ``OpenAiConfig``
     - ``"openai"``
     - ``"openai"``
     - (existing field)
   * - ``OciGenAiConfig``
     - (existing field)
     - ``"oci"``
     - (existing field)
   * - ``OpenAiCompatibleConfig``
     - (unknown)
     - (unknown)
     - (existing field)
   * - ``VllmConfig``
     - (unknown)
     - ``"vllm"``
     - (inherited)
   * - ``OllamaConfig``
     - (unknown)
     - ``"ollama"``
     - (inherited)

Well-known values
^^^^^^^^^^^^^^^^^

The spec documents recommended string values for each field.  These are not
enforced at the schema level -- they serve as conventions that adapters and
documentation can rely on.

**provider** (model provider)

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Description
   * - ``"openai"``
     - OpenAI models (GPT-4o, o1, etc.)
   * - ``"anthropic"``
     - Anthropic models (Claude family)
   * - ``"meta"``
     - Meta models (Llama family)
   * - ``"cohere"``
     - Cohere models (Command family)
   * - ``"google"``
     - Google models (Gemini family)
   * - ``"mistral"``
     - Mistral AI models

**api_provider** (API provider)

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Description
   * - ``"openai"``
     - OpenAI platform API
   * - ``"oci"``
     - OCI Generative AI service
   * - ``"aws_bedrock"``
     - AWS Bedrock
   * - ``"vertex_ai"``
     - Google Vertex AI
   * - ``"azure_openai"``
     - Azure OpenAI Service
   * - ``"vllm"``
     - vLLM self-hosted deployment
   * - ``"ollama"``
     - Ollama local deployment

**api_type** (wire protocol)

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Description
   * - ``"chat_completions"``
     - OpenAI Chat Completions API
   * - ``"responses"``
     - OpenAI Responses API

Adapter dispatch strategy
^^^^^^^^^^^^^^^^^^^^^^^^^

Framework adapters dispatch on the ``api_provider`` string (and optionally
``api_type``) to select the appropriate client configuration.  This is a
plain string match -- no provider registry or class hierarchy is required.

When a ``LlmConfig`` subclass is used (e.g. ``OpenAiConfig``), the adapter
handles it through the existing class-based dispatch.  When a bare
``LlmConfig`` instance is used, the adapter falls back to string-based
dispatch on ``api_provider``.  Each adapter should raise a clear error for
unsupported ``api_provider`` values.

YAML examples
^^^^^^^^^^^^^

**OpenAI (bare LlmConfig)**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: openai-gpt4o
   spec:
     model_id: gpt-4o
     provider: openai
     api_provider: openai
     api_type: chat_completions

**Meta model on AWS Bedrock**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: bedrock-llama
   spec:
     model_id: meta.llama3-1-70b-instruct-v1:0
     provider: meta
     api_provider: aws_bedrock

**Anthropic model on AWS Bedrock**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: bedrock-claude
   spec:
     model_id: anthropic.claude-sonnet-4-20250514-v1:0
     provider: anthropic
     api_provider: aws_bedrock

**Google model on Vertex AI**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: vertex-gemini
   spec:
     model_id: gemini-2.0-flash
     provider: google
     api_provider: vertex_ai

**Cohere model on OCI GenAI via OpenAI protocol**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: oci-cohere
   spec:
     model_id: cohere.command-r-plus
     provider: cohere
     api_provider: oci
     api_type: chat_completions

**vLLM (self-hosted)**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: vllm-llama
   spec:
     model_id: meta-llama/Llama-3.1-70B-Instruct
     provider: meta
     api_provider: vllm
     api_type: chat_completions

**Ollama (local)**

.. code-block:: yaml

   kind: LlmConfig
   apiVersion: v26.2.0
   metadata:
     name: ollama-llama
   spec:
     model_id: llama3.1
     provider: meta
     api_provider: ollama

Backward compatibility
^^^^^^^^^^^^^^^^^^^^^^

- ``LlmConfig`` becomes non-abstract.  This is an additive change -- all
  existing subclasses continue to compile and work unchanged.
- The three new fields (``provider``, ``api_provider``, ``api_type``) are
  optional with ``None`` defaults, so existing YAML files that omit them
  remain valid.
- The minimum ``apiVersion`` for the new fields is ``v26.2.0``; older spec
  versions silently exclude them.
- No existing YAML files need to be modified.

Potential risks or concerns
---------------------------

- **Free-form strings.**
  Because ``provider``, ``api_provider``, and ``api_type`` are unconstrained
  strings, typos (e.g. ``"opanai"``) produce runtime errors rather than
  schema-level validation failures.  The well-known values list in
  documentation mitigates this, and adapters should surface clear error
  messages for unrecognized values.

- **Adapter complexity for non-OpenAI protocols.**
  Providers with proprietary APIs (Bedrock, Vertex AI) require dedicated client
  logic inside every adapter.  This shifts complexity from the spec into
  adapter implementations.

- **Naming conventions.**
  There is no enforced convention for string values (e.g.
  ``"aws_bedrock"`` vs. ``"bedrock"`` vs. ``"amazon_bedrock"``).  The
  well-known values list establishes canonical names.
