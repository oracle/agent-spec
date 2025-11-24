LLMs
====

This page presents all APIs and classes related to LLM models.

LlmConfig
---------

.. _llmconfig:
.. autoclass:: pyagentspec.llms.llmconfig.LlmConfig
    :exclude-members: model_post_init, model_config


LLM Generation Config
---------------------

Parameters for LLM generation (``max_tokens``, ``temperature``, ``top_p``).

.. _llmgenerationconfig:
.. autoclass:: pyagentspec.llms.llmgenerationconfig.LlmGenerationConfig
    :exclude-members: model_post_init, model_config, model_dump, model_dump_json

OpenAI API Type 
---------------

.. _openaiapitype:
.. autoclass:: pyagentspec.llms.openaicompatibleconfig.OpenAIAPIType


.. _allllms:

All models
----------

OpenAI Compatible Models
^^^^^^^^^^^^^^^^^^^^^^^^

.. _openaicompatiblemodel:
.. autoclass:: pyagentspec.llms.openaicompatibleconfig.OpenAiCompatibleConfig
    :exclude-members: model_post_init, model_config

VLLM Models
'''''''''''

.. _vllmconfig:
.. autoclass:: pyagentspec.llms.vllmconfig.VllmConfig
    :exclude-members: model_post_init, model_config

Ollama Models
'''''''''''''

.. _ollamaconfig:
.. autoclass:: pyagentspec.llms.ollamaconfig.OllamaConfig
    :exclude-members: model_post_init, model_config

OpenAI Models
^^^^^^^^^^^^^

.. _openaiconfig:
.. autoclass:: pyagentspec.llms.openaiconfig.OpenAiConfig
    :exclude-members: model_post_init, model_config

OciGenAi Models
^^^^^^^^^^^^^^^

.. _servingmode:
.. autoclass:: pyagentspec.llms.ocigenaiconfig.ServingMode

.. _modelprovider:
.. autoclass:: pyagentspec.llms.ocigenaiconfig.ModelProvider

.. _ocigenaiconfig:
.. autoclass:: pyagentspec.llms.ocigenaiconfig.OciGenAiConfig
    :exclude-members: model_post_init, model_config

.. _ociclientconfig:
.. autoclass:: pyagentspec.llms.ociclientconfig.OciClientConfig
    :exclude-members: model_post_init, model_config

.. _ociclientconfigwithapikey:
.. autoclass:: pyagentspec.llms.ociclientconfig.OciClientConfigWithApiKey
    :exclude-members: model_post_init, model_config

.. _ociclientconfigwithsecuritytoken:
.. autoclass:: pyagentspec.llms.ociclientconfig.OciClientConfigWithSecurityToken
    :exclude-members: model_post_init, model_config

.. _ociclientconfigwithinstanceprincipal:
.. autoclass:: pyagentspec.llms.ociclientconfig.OciClientConfigWithInstancePrincipal
    :exclude-members: model_post_init, model_config

.. _ociclientconfigwithresourceprincipal:
.. autoclass:: pyagentspec.llms.ociclientconfig.OciClientConfigWithResourcePrincipal
    :exclude-members: model_post_init, model_config
