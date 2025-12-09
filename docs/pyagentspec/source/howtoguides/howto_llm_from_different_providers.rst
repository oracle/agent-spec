============================================
How to Use LLMs from Different LLM Providers
============================================

Agent Spec supports several LLM providers, each one having its own LlmConfig component.
The available LLMs are:

- :ref:`OpenAiConfig <openaiconfig>`
- :ref:`OciGenAiConfig <ocigenaiconfig>`
- :ref:`OpenAiCompatibleConfig <openaicompatiblemodel>`
- :ref:`VllmConfig <vllmconfig>`
- :ref:`OllamaConfig <ollamaconfig>`

Their configuration is specified directly in their respective class constructor.
This guide will show you how to configure LLMs from different LLM providers with examples and notes on usage.


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


OpenAiCompatibleConfig
======================

OpenAI Compatible LLMs are all those models that are served through OpenAI APIs, either responses or completions.
The ``OpenAiCompatibleConfig`` allows users to use this type of models in their agents and flows.

**Parameters**

.. option:: model_id: str

  Name of the model to use.

.. option:: url: str

  Hostname and port of the vLLM server where the model is hosted.

.. option:: api_type: str

  The API type that should be used. Can be either ``chat_completions`` or ``responses``.

.. option:: default_generation_parameters: dict, null

  Default parameters for text generation with this model.

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
