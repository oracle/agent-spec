:orphan:

==================================
RFC: Generic LLM Configuration
==================================

This RFC proposes a ``GenericLlmConfig`` component for
`Open Agent Spec <https://github.com/oracle/agent-spec>`_ that provides a
provider-agnostic way to configure LLM connections using a string-based
provider discriminator and an open-ended provider configuration object.

Summary
-------

Add a ``GenericLlmConfig`` component that can describe any LLM provider
through a ``provider.type`` string discriminator and a flexible
``ProviderConfig`` object, without requiring a new ``LlmConfig`` subclass per
provider.

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

The proposal introduces a new ``GenericLlmConfig`` component with its
supporting ``ProviderConfig`` model.

``ProviderConfig``
^^^^^^^^^^^^^^^^^^

Identifies the provider and optionally overrides the endpoint, wire protocol,
and API version.  The schema is open-ended: authors can pass provider-specific
keys (e.g. ``region``, ``project_id``, ``deployment_name``) without a schema
change.

.. code-block:: yaml

   provider:
     type: <string>              # required — e.g. "openai", "anthropic", "aws_bedrock"
     endpoint: <string>          # optional — base URL override
     api_protocol: <string>      # optional — e.g. "openai_chat_completions"
     api_version: <string>       # optional — API version string
     # additional provider-specific fields are permitted

See `Well-known provider configs`_ for typed subclasses that declare explicit
fields per provider type.

``AuthConfig``
^^^^^^^^^^^^^^

Different providers require different authentication mechanisms.
``AuthConfig`` uses a ``type`` discriminator to select the mechanism and an
open-ended schema for mechanism-specific fields.  ``AuthConfig`` handles
**credentials only** -- routing fields (``endpoint``, ``region``,
``project_id``) belong in ``ProviderConfig``.

.. code-block:: yaml

   auth:
     type: <string>       # required — one of the well-known types below
     # ... mechanism-specific fields

Well-known auth types
"""""""""""""""""""""

**1. api_key** -- for providers that use static API keys (OpenAI, Anthropic,
Mistral, Cohere, etc.).

.. code-block:: yaml

   auth:
     type: api_key
     value: <string>              # required — the API key
     header_name: <string>        # optional — override the HTTP header
                                  #   default: "Authorization" with "Bearer {value}"
                                  #   e.g. "x-api-key", "api-key"

.. code-block:: yaml

   # OpenAI
   auth:
     type: api_key
     value: "OPENAI_API_KEY"

   # Anthropic (custom header)
   auth:
     type: api_key
     value: "ANTHROPIC_API_KEY"
     header_name: "x-api-key"

**2. aws** -- for AWS Bedrock.  All credential fields are optional; omitting
them delegates to the default AWS credential chain
(env -> file -> instance profile).

.. code-block:: yaml

   auth:
     type: aws
     access_key_id: <string>           # optional — static credentials
     secret_access_key: <string>       # optional — static credentials
     session_token: <string>           # optional — for temporary credentials
     role_arn: <string>                # optional — assume this role via STS
     external_id: <string>             # optional — for cross-account role assumption
     profile: <string>                 # optional — named profile from ~/.aws/credentials

.. code-block:: yaml

   # Production on AWS (instance profile / task role — no explicit credentials)
   auth:
     type: aws

   # Local dev with named profile
   auth:
     type: aws
     profile: bedrock-dev

   # Cross-account role assumption
   auth:
     type: aws
     role_arn: "arn:aws:iam::123456789012:role/bedrock-access"
     external_id: "my-external-id"

   # Explicit static credentials (CI/testing)
   auth:
     type: aws
     access_key_id: "AWS_ACCESS_KEY_ID"
     secret_access_key: "AWS_SECRET_ACCESS_KEY"

**3. gcp** -- for Google Vertex AI.  All credential fields are optional;
omitting them delegates to Application Default Credentials (ADC).

.. code-block:: yaml

   auth:
     type: gcp
     credentials_file: <string>                 # optional — path to service account JSON
     credentials_json: <string>                 # optional — inline service account JSON
     impersonate_service_account: <string>      # optional — SA email to impersonate
     workforce_pool_provider: <string>          # optional — workload identity federation

.. code-block:: yaml

   # Production on GCP (attached service account / ADC — no explicit credentials)
   auth:
     type: gcp

   # Local dev with explicit key file
   auth:
     type: gcp
     credentials_file: "/path/to/service-account.json"

   # CI with inline credentials from env
   auth:
     type: gcp
     credentials_json: "GCP_SERVICE_ACCOUNT_JSON"

   # Service account impersonation
   auth:
     type: gcp
     impersonate_service_account: "vertex-sa@my-project.iam.gserviceaccount.com"

**4. azure** -- for Azure OpenAI.  Supports managed identity, service
principal, or API key.  Omitting all credential fields delegates to
``DefaultAzureCredential``.

.. code-block:: yaml

   auth:
     type: azure
     api_key: <string>                 # optional — Azure-issued API key
     client_id: <string>               # optional — managed identity or service principal
     client_secret: <string>           # optional — service principal secret
     tenant_id: <string>               # optional — AAD tenant for service principal
     use_managed_identity: <bool>      # optional — explicitly use managed identity

.. code-block:: yaml

   # DefaultAzureCredential (no explicit credentials)
   auth:
     type: azure

   # Managed identity on Azure compute
   auth:
     type: azure
     use_managed_identity: true

   # Azure API key
   auth:
     type: azure
     api_key: "AZURE_OPENAI_API_KEY"

   # Service principal (CI/CD)
   auth:
     type: azure
     tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
     client_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
     client_secret: "AZURE_CLIENT_SECRET"

**5. oauth2** -- for providers requiring OAuth2 client credentials or token
exchange flows.

.. code-block:: yaml

   auth:
     type: oauth2
     token_url: <string>              # required — token endpoint
     client_id: <string>              # required
     client_secret: <string>          # required
     scopes: [<string>]               # optional — list of scopes
     audience: <string>               # optional — token audience

.. code-block:: yaml

   auth:
     type: oauth2
     token_url: "https://auth.example.com/oauth/token"
     client_id: "OAUTH_CLIENT_ID"
     client_secret: "OAUTH_CLIENT_SECRET"
     scopes: ["inference.run"]

Validation rules
""""""""""""""""

1. ``type`` is always required.
2. Each type has its own required/optional fields as documented above.
3. For ``aws``/``gcp``/``azure``: if no explicit credentials are provided,
   the runtime delegates to the platform SDK's default credential chain.
   This is the recommended approach for production.
4. Mutually exclusive fields (e.g. ``azure.api_key`` vs.
   ``azure.client_id``) should raise a validation error if both are set.

Like ``ProviderConfig``, the schema is open-ended so new auth mechanisms can
be introduced without a spec change.  SDKs and adapters **should** validate
the well-known auth types and surface clear errors for missing fields.

``GenericLlmConfig``
^^^^^^^^^^^^^^^^^^^^

The new component is a separate top-level Agent Spec component (not a
subclass of ``LlmConfig``) and declares a minimum spec version of ``v26.2.0``.

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   spec:
     model_id: <string>            # required — e.g. "gpt-4o", "claude-sonnet-4-20250514"
     provider: <ProviderConfig>    # required — provider configuration (see above)
     auth: <AuthConfig>            # optional — authentication configuration (see above)
     provider_extensions:          # optional — non-portable escape hatch
       <string>: <any>

``provider_extensions`` provides a non-portable escape hatch for
provider-specific options that do not belong in ``ProviderConfig``.

Relationship to existing configs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``GenericLlmConfig`` exists alongside the existing ``LlmConfig`` subclasses.
The following table shows how existing configs map conceptually to
``GenericLlmConfig``:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Existing config
     - provider.type
     - Notes
   * - ``OpenAiConfig``
     - ``"openai"``
     - Fixed provider; ``model_id`` maps directly, ``api_key`` maps to
       ``auth: {type: api_key, value: ...}``
   * - ``OpenAiCompatibleConfig``
     - (varies)
     - ``url`` maps to ``provider.endpoint``; ``api_type`` maps to
       ``provider.api_protocol``
   * - ``VllmConfig``
     - ``"vllm"``
     - Inherits from ``OpenAiCompatibleConfig``; no additional fields
   * - ``OllamaConfig``
     - ``"ollama"``
     - Inherits from ``OpenAiCompatibleConfig``; no additional fields

Users can choose either the provider-specific config or ``GenericLlmConfig``
to describe the same LLM connection.  Adapters handle both paths
independently.

YAML examples
^^^^^^^^^^^^^

**OpenAI**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: openai-gpt4o
   spec:
     model_id: gpt-4o
     provider:
       type: openai
     auth:
       type: api_key
       value: "OPENAI_API_KEY"

**Anthropic**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: claude-sonnet
   spec:
     model_id: claude-sonnet-4-20250514
     provider:
       type: anthropic
     auth:
       type: api_key
       value: "ANTHROPIC_API_KEY"

**Azure OpenAI (API key)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: azure-gpt4o
   spec:
     model_id: gpt-4o
     provider:
       type: azure_openai
       endpoint: https://my-resource.openai.azure.com
       api_version: "2024-06-01"
       deployment_name: gpt4o-deploy
     auth:
       type: azure
       api_key: "AZURE_OPENAI_API_KEY"

**Azure OpenAI (managed identity)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: azure-gpt4o-mi
   spec:
     model_id: gpt-4o
     provider:
       type: azure_openai
       endpoint: https://my-resource.openai.azure.com
       api_version: "2024-06-01"
       deployment_name: gpt4o-deploy
     auth:
       type: azure
       use_managed_identity: true

**AWS Bedrock (default credential chain)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: bedrock-claude
   spec:
     model_id: anthropic.claude-sonnet-4-20250514-v1:0
     provider:
       type: aws_bedrock
       region: us-east-1
     auth:
       type: aws

**AWS Bedrock (cross-account role)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: bedrock-claude-xacct
   spec:
     model_id: anthropic.claude-sonnet-4-20250514-v1:0
     provider:
       type: aws_bedrock
       region: us-east-1
     auth:
       type: aws
       role_arn: "arn:aws:iam::123456789012:role/bedrock-access"

**Google Vertex AI (ADC)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: vertex-gemini
   spec:
     model_id: gemini-2.0-flash
     provider:
       type: gcp_vertex_ai
       project_id: my-gcp-project
       region: us-central1
     auth:
       type: gcp

**Google Vertex AI (service account)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: vertex-gemini-sa
   spec:
     model_id: gemini-2.0-flash
     provider:
       type: gcp_vertex_ai
       project_id: my-gcp-project
       region: us-central1
     auth:
       type: gcp
       credentials_file: "/path/to/service-account.json"

**vLLM (self-hosted)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: vllm-llama
   spec:
     model_id: meta-llama/Llama-3.1-70B-Instruct
     provider:
       type: vllm
       endpoint: http://localhost:8000

**Ollama (local)**

.. code-block:: yaml

   kind: GenericLlmConfig
   apiVersion: v26.2.0
   metadata:
     name: ollama-llama
   spec:
     model_id: llama3.1
     provider:
       type: ollama
       endpoint: http://localhost:11434

Adapter dispatch strategy
^^^^^^^^^^^^^^^^^^^^^^^^^

Framework adapters dispatch on the ``provider.type`` string to select the
appropriate client configuration.  This is a plain string match -- no provider
registry or class hierarchy is required.  Each adapter (LangGraph, OpenAI
Agents SDK, AutoGen, Agent Framework) implements this dispatch independently
and should raise a clear error for unsupported provider types.

Well-known provider configs
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because ``ProviderConfig`` uses ``extra="allow"``, provider-specific fields
(e.g. ``deployment_name``, ``region``) are accepted but not validated or
discoverable through the schema.  To address this, the spec defines
**well-known provider config subclasses** that inherit from ``ProviderConfig``
and declare explicit, typed fields for each major provider.

Design
""""""

Each well-known provider config is a Pydantic model that:

1. **Inherits from** ``ProviderConfig`` -- it gets ``type``, ``endpoint``,
   ``api_protocol``, and ``api_version`` for free.
2. **Fixes** ``type`` to a literal value (e.g. ``Literal["aws_bedrock"]``) so
   it cannot be mis-set.
3. **Declares** provider-specific fields with proper types, defaults, and
   descriptions -- enabling schema validation, IDE auto-completion, and
   documentation generation.
4. **Retains** ``extra="allow"`` so forward-compatible fields are still
   accepted without a spec change.

These are **not** new spec components.  They are model subclasses used
internally by ``GenericLlmConfig`` to type the ``provider`` field more
precisely.  ``GenericLlmConfig`` remains the only component kind; the
subclass is selected automatically based on ``provider.type`` during
deserialization.

Resolution strategy
"""""""""""""""""""

When ``GenericLlmConfig`` deserializes the ``provider`` field, it inspects the
``type`` value and selects the appropriate subclass:

1. If ``type`` matches a well-known provider (e.g. ``"aws_bedrock"``), the
   corresponding subclass (``AwsBedrockProviderConfig``) is used.  Required
   fields are validated at parse time.
2. If ``type`` does not match any well-known provider, the base
   ``ProviderConfig`` is used with ``extra="allow"``.  No validation is
   performed beyond the base fields.

This can be implemented via a Pydantic discriminated union on ``type``, with
``ProviderConfig`` as the fallback default.

Well-known subclasses
"""""""""""""""""""""

**AwsBedrockProviderConfig**

.. code-block:: python

   class AwsBedrockProviderConfig(ProviderConfig):
       type: Literal["aws_bedrock"] = "aws_bedrock"
       region: str                           # required — AWS region

.. code-block:: yaml

   provider:
     type: aws_bedrock
     region: us-east-1

**AzureOpenAiProviderConfig**

.. code-block:: python

   class AzureOpenAiProviderConfig(ProviderConfig):
       type: Literal["azure_openai"] = "azure_openai"
       deployment_name: str                  # required — Azure deployment name
       resource_group: Optional[str] = None  # optional — Azure resource group

.. code-block:: yaml

   provider:
     type: azure_openai
     endpoint: https://my-resource.openai.azure.com
     api_version: "2024-06-01"
     deployment_name: gpt4o-deploy
     resource_group: my-rg                  # optional

**GcpVertexAiProviderConfig**

.. code-block:: python

   class GcpVertexAiProviderConfig(ProviderConfig):
       type: Literal["gcp_vertex_ai"] = "gcp_vertex_ai"
       project_id: str                       # required — GCP project ID
       region: str                           # required — GCP region

.. code-block:: yaml

   provider:
     type: gcp_vertex_ai
     project_id: my-gcp-project
     region: us-central1

Summary table
"""""""""""""

.. list-table::
   :header-rows: 1
   :widths: 20 30 10 40

   * - Subclass
     - Field
     - Required
     - Description
   * - ``AwsBedrockProviderConfig``
     - ``region``
     - Yes
     - AWS region (e.g. ``"us-east-1"``)
   * - ``AzureOpenAiProviderConfig``
     - ``deployment_name``
     - Yes
     - Azure deployment name
   * - ``AzureOpenAiProviderConfig``
     - ``resource_group``
     - No
     - Azure resource group
   * - ``GcpVertexAiProviderConfig``
     - ``project_id``
     - Yes
     - GCP project ID
   * - ``GcpVertexAiProviderConfig``
     - ``region``
     - Yes
     - GCP region (e.g. ``"us-central1"``)

Extensibility
"""""""""""""

New well-known provider configs can be added in future spec versions by
creating additional ``ProviderConfig`` subclasses.  This does **not** require
changes to ``GenericLlmConfig`` itself -- only an update to the discriminated
union mapping.

Providers without a well-known subclass continue to use the base
``ProviderConfig`` with ``extra="allow"``, requiring no spec change at all.

Why subclasses, not separate components?
""""""""""""""""""""""""""""""""""""""""

The well-known provider configs are **model subclasses**, not standalone spec
components (i.e. they do not have their own ``kind``).  This is intentional:

- ``GenericLlmConfig`` remains the single entry point.  Users never need to
  choose between ``kind: GenericLlmConfig`` and
  ``kind: AwsBedrockGenericLlmConfig``.
- The ``provider.type`` string is the sole discriminator.  Adding a subclass
  does not change the YAML surface -- only validation strictness.
- Adapters continue to dispatch on ``provider.type``.  The subclass gives
  them typed access to fields (``provider.region`` instead of
  ``provider.model_extra["region"]``) but does not change the dispatch logic.

Backward compatibility
^^^^^^^^^^^^^^^^^^^^^^

- ``GenericLlmConfig`` introduces a new ``component_type`` value
  (``kind: GenericLlmConfig``).  Existing configs (``OpenAiConfig``,
  ``OciGenAiConfig``, etc.) continue to work unchanged.
- The minimum ``apiVersion`` is ``v26.2.0``; older spec versions silently
  exclude the new fields.
- No existing YAML files need to be modified.

Potential risks or concerns
---------------------------

- **Free-form ``provider.type``.**
  Because ``provider.type`` is an unconstrained string, typos (e.g.
  ``"opanai"``) produce runtime errors rather than schema-level validation
  failures.  A recommended-values list in documentation could mitigate this.

- **Adapter complexity for non-OpenAI protocols.**
  Providers with proprietary APIs (Bedrock, Vertex AI) require dedicated client
  logic inside every adapter.  This shifts complexity from the spec into
  adapter implementations.

- **Naming conventions.**
  There is no enforced convention for ``provider.type`` strings (e.g.
  ``"aws_bedrock"`` vs. ``"bedrock"`` vs. ``"amazon_bedrock"``).  Documentation
  should establish canonical names.

- **``extra="allow"`` discoverability.**
  Extra fields on the base ``ProviderConfig`` are not visible in the JSON
  schema.  The *Well-known provider configs* described above address this for
  major providers by declaring explicit fields that surface in validation
  errors, IDE auto-completion, and generated documentation.  Unknown providers
  still rely on ``extra="allow"`` and external documentation.

