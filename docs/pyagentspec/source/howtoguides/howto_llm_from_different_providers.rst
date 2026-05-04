============================================
How to Use LLMs from Different LLM Providers
============================================

Agent Spec supports several LLM providers. ``LlmConfig`` can be used directly with the ``api_provider``
field to describe any provider, or you can use a dedicated subclass for provider-specific configuration.
The available LLM configurations are:

- :ref:`LlmConfig <llmconfig>` (generic, provider-agnostic)
- :ref:`OpenAiConfig <openaiconfig>`
- :ref:`GeminiConfig <geminiconfig>`
- :ref:`OciGenAiConfig <ocigenaiconfig>`
- :ref:`OpenAiCompatibleConfig <openaicompatibleconfig>`
- :ref:`VllmConfig <vllmconfig>`
- :ref:`OllamaConfig <ollamaconfig>`

Their configuration is specified directly in their respective class constructor.
This guide will show you how to configure LLMs from different LLM providers with examples and notes on usage.

.. _howto-llmwithretrypolicy:

Configure retry behavior for remote LLM calls
=============================================

All ``LlmConfig`` subclasses accept an optional ``retry_policy`` parameter.
Use it to configure retry attempts, per-request timeouts, and backoff behavior
for transient failures when calling remote LLM endpoints.

For example, you can attach a retry policy directly to a ``VllmConfig``:

.. literalinclude:: ../code_examples/howto_generation_config.py
    :language: python
    :start-after: # .. llm_retry_policy:
    :end-before: # .. end-llm_retry_policy

API Reference: :ref:`LlmConfig <llmconfig>`, :ref:`RetryPolicy <retrypolicy>`


LlmConfig (Generic)
====================

``LlmConfig`` can be used directly to describe any LLM without requiring a provider-specific subclass.
This is useful when you want to describe an LLM from a provider that does not have a dedicated configuration class,
or when you want a simple, portable configuration.

**Parameters**

.. option:: model_id: str

  Identifier of the model to use, as expected by the selected API provider.

.. option:: provider: str, null

  The model provider, i.e. who made the model (e.g. ``"openai"``, ``"meta"``, ``"anthropic"``, ``"cohere"``).

.. option:: api_provider: str, null

  The API provider, i.e. who serves the API (e.g. ``"openai"``, ``"oci"``, ``"vllm"``, ``"ollama"``, ``"aws_bedrock"``, ``"vertex_ai"``).

.. option:: api_type: str, null

  The API format to use to interact with the LLM (e.g. ``"chat_completions"``, ``"responses"``).

.. option:: url: str, null

  URL of the API endpoint (e.g. ``"https://api.openai.com/v1"``).

.. option:: api_key: str, null

  An optional API key for the remote LLM. When exported, the value is replaced by a reference.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. llmconfig-start
    :end-before: .. llmconfig-end


OciGenAiConfig
==============

`OCI GenAI Configuration <https://docs.oracle.com/iaas/Content/generative-ai/overview.htm>`_ refers to model served
by `OCI Generative AI <https://www.oracle.com/artificial-intelligence/generative-ai/generative-ai-service/>`_.

**Parameters**

.. option:: model_id: str

  Name of the model to use. A list of the available models is given in
  `Oracle OCI Documentation <https://docs.oracle.com/en-us/iaas/Content/generative-ai/deprecating.htm#>`_
  under the Model Retirement Dates (On-Demand Mode) section.

.. option:: compartment_id: str

  The OCID (Oracle Cloud Identifier) of a compartment within your tenancy.

.. option:: serving_mode: str

  The mode how the model specified is served:

  - ``ON_DEMAND``: the model is hosted in a shared environment;
  - ``DEDICATED``: the model is deployed in a customer-dedicated environment.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

  Example:

  .. code-block:: python

    default_generation_parameters = LlmGenerationConfig(max_tokens=256, temperature=0.8)

.. option:: client_config: OciClientConfig, null

  OCI client config to authenticate the OCI service.
  See the below examples for the usage and more information.

OCI Client Configuration
------------------------

OCI GenAI models require a client configuration that contains all the settings needed to perform
the authentication to use OCI services. The ``OciClientConfig`` holds these settings.

**Parameters**

.. option:: service_endpoint: str

  The endpoint URL for the OCIGenAI service. Make sure you set the region right.
  For doing so, make sure that the Region where your private key is created,
  is aligned with the region mention in the ``service_endpoint``.

.. option:: auth_type: str

  The authentication type to use, e.g., ``API_KEY``,
  ``SECURITY_TOKEN``,
  ``INSTANCE_PRINCIPAL`` (It means that you need to execute the code from a compartment enabled for OCIGenAI.),
  ``RESOURCE_PRINCIPAL``.


Based on the type of authentication the user wants to adopt, different specifications of the ``OciClientConfig``
are defined. Indeed, the ``OciClientConfig`` component is abstract, and should not be used directly.
In the following sections we show what client extensions are available and their specific parameters.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. oci-start
    :end-before: .. oci-end


OciClientConfigWithSecurityToken
--------------------------------

Client configuration that should be used if users want to use authentication through security token.

**Parameters**

.. option:: auth_file_location: str

  The location of the authentication file from which the authentication information should be retrieved.
  The default location is ``~/.oci/config``.

.. option:: auth_profile: str

  The name of the profile to use, among the ones defined in the authentication file.
  The default profile name is ``DEFAULT``.

OciClientConfigWithApiKey
-------------------------

Client configuration that should be used if users want to use authentication with API key.
The parameters required are the same defined for the ``OciClientConfigWithSecurityToken``.


OciClientConfigWithInstancePrincipal
------------------------------------

Client configuration that should be used if users want to use instance principal authentication.
No additional parameters are required.


OciClientConfigWithResourcePrincipal
------------------------------------

Client configuration that should be used if users want to use resource principal authentication.
No additional parameters are required.


OpenAiConfig
============

OpenAI Models are powered by `OpenAI <https://platform.openai.com/docs/models>`_.
You can refer to one of those models by using the ``OpenAiConfig`` Component.

**Parameters**

.. option:: model_id: str

  Name of the model to use.

.. option:: api_type: str

  The API type that should be used. Can be either ``chat_completions`` or ``responses``.

.. option:: api_key: str, null

  An optional api key for the authentication with the OpenAI endpoint.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

.. important::
   Ensure that the ``OPENAI_API_KEY`` is set beforehand
   to access this model. A list of available OpenAI models can be found at
   the following link: `OpenAI Models <https://platform.openai.com/docs/models>`_.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. openai-start
    :end-before: .. openai-end

.. _howto-openaicompatibleconfig:

GeminiConfig
============

`Gemini <https://gemini.google.com/>`_ models can be configured through ``GeminiConfig``.
Agent Spec supports both Google AI Studio and Google Vertex AI authentication modes.

Gemini authentication is modeled as a nested auth component, similar to OCI ``client_config``.
The auth component itself remains inline during serialization. When ``api_key`` or
``credentials`` is provided explicitly, only that sensitive field is externalized and must
be supplied through ``components_registry`` when loading the configuration back.

**Parameters**

.. option:: model_id: str

  Name of the model to use, for example ``gemini-2.5-flash`` or
  ``gemini-2.0-flash-lite``.

.. option:: auth: GeminiAuthConfig

  Required authentication component for Gemini. As with other Agent Spec components,
  auth configs need a ``name``. Use ``GeminiAIStudioAuthConfig(name="gemini-aistudio-auth")``
  if you want runtimes to load ``GEMINI_API_KEY`` from the environment, or
  ``GeminiVertexAIAuthConfig(name="gemini-vertex-auth", ...)`` for Vertex AI.
  The auth component remains inline when serialized. If ``api_key`` or ``credentials``
  is set explicitly, only that sensitive field is serialized as a reference.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

Google AI Studio authentication
-------------------------------

Use ``GeminiAIStudioAuthConfig`` when connecting through Google AI Studio.

**Parameters**

.. option:: api_key: str, null

  Optional Gemini API key. If omitted, runtimes may load it from ``GEMINI_API_KEY``.
  If provided explicitly, only the ``api_key`` field is externalized during
  serialization and must be supplied separately when deserializing.

**Example**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. gemini-aistudio-start
    :end-before: .. gemini-aistudio-end

Vertex AI authentication
------------------------

Use ``GeminiVertexAIAuthConfig`` when connecting through Google Vertex AI.

**Parameters**

.. option:: project_id: str, null

  Optional Google Cloud project identifier.
  In practice, you may still need to set this explicitly when ADC provides
  credentials but does not expose a default project.

.. option:: location: str

  Vertex AI location or region. Defaults to ``global``.

.. option:: credentials: str | dict, null

  Optional local file path (``str``) to a Google Cloud JSON credential file, such as a
  service-account key file, or an inline ``dict`` containing the parsed JSON contents of
  that file.
  When omitted, runtimes may rely on Google Application Default Credentials (ADC), such as
  ``GOOGLE_APPLICATION_CREDENTIALS``, credentials made available through the local
  Google Cloud environment, or an attached service account.
  See `Google Cloud authentication docs <https://cloud.google.com/docs/authentication/application-default-credentials>`_
  for details.
  This does not guarantee that ``project_id`` can also be inferred automatically.
  If provided explicitly, only the ``credentials`` field is externalized during
  serialization. Non-secret auth settings such as ``project_id`` and ``location``
  remain inline in the main config.

**Example**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. gemini-vertex-start
    :end-before: .. gemini-vertex-end


OpenAiCompatibleConfig
======================

OpenAI Compatible LLMs are all those models that are served through OpenAI APIs, either responses or completions.
The ``OpenAiCompatibleConfig`` allows users to use this type of models in their agents and flows.

**Parameters**

.. option:: model_id: str

  Name of the model to use.

.. option:: url: str

  Hostname and port of the server exposing the OpenAI-compatible endpoint.

.. option:: api_type: str

  The API type that should be used. Can be either ``chat_completions`` or ``responses``.

.. option:: api_key: str, null

  An optional api key if the remote server requires it.

.. option:: key_file: str, null

  Path to an optional client private key file in PEM format.

.. option:: cert_file: str, null

  Path to an optional client certificate chain file in PEM format.

.. option:: ca_file: str, null

  Path to an optional trusted CA certificate file in PEM format, used to verify the server.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

The certificate fields are useful when the remote endpoint is exposed over HTTPS with a private CA
or when it requires mutual TLS (mTLS). Like ``api_key``, these values are treated as sensitive
fields during serialization.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. openaicompatible-start
    :end-before: .. openaicompatible-end


VllmConfig
==========

`vLLM Models <https://docs.vllm.ai/en/latest/models/supported_models.html>`_ are models hosted with a vLLM server.
The ``VllmConfig`` allows users to use this type of models in their agents and flows.

**Parameters**

.. option:: model_id: str

  Name of the model to use.

.. option:: url: str

  Hostname and port of the vLLM server where the model is hosted.

.. option:: api_type: str

  The API type that should be used. Can be either ``chat_completions`` or ``responses``.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

.. option:: api_key: str, null

  An optional api key if the remote vllm server requires it.

The ``VllmConfig`` inherits from ``OpenAiCompatibleConfig``, so it also supports the optional
``key_file``, ``cert_file``, and ``ca_file`` parameters for HTTPS and mTLS connections.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. vllm-start
    :end-before: .. vllm-end


OllamaConfig
============

`Ollama Models <https://ollama.com/>`_ are powered by a locally hosted Ollama server.
The ``OllamaConfig`` allows users to use this type of models in their agents and flows.

**Parameters**

.. option:: model_id: str

  Name of the model to use.

.. option:: url: str

  Hostname and port of the vLLM server where the model is hosted.

.. option:: api_type: str

  The API type that should be used. Can be either ``chat_completions`` or ``responses``.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

.. option:: api_key: str, null

  An optional api key if the ollama server requires it.

**Examples**

.. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
    :language: python
    :start-after: .. ollama-start
    :end-before: .. ollama-end


Recap
=====

This guide provides detailed descriptions of each model type supported by Agent Spec,
demonstrating how to declare them using PyAgentSpec syntax.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_llm_from_different_providers.py
        :language: python
        :linenos:
        :start-after: .. full-code-start
        :end-before: .. full-code-end


Next steps
==========

Having learned how to configure LLMs from different providers, you may now proceed to:

- :doc:`How to Build LLM Generation Configurations <howto_generation_config>`
- :doc:`How to Build an Agent with Remote Tools <howto_agent_with_remote_tools>`
