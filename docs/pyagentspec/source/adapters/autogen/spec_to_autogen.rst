.. _spectoautogen:

Run Agent Spec configurations with AutoGen
==========================================

This usage example showcases the creation of a simple Agent Spec Agent, subsequently serialized into JSON and converted into an AutoGen
assistant. Also includes mapping of a `ServerTool` and execution of the conversation.

.. literalinclude:: ../../code_examples/adapter_autogen_quickstart.py
    :language: python
    :start-after: .. start-agentspec_to_runtime
    :end-before: .. end-agentspec_to_runtime

OCI Generative AI models
------------------------

Agents configured with an ``OciGenAiConfig`` run on AutoGen through the OpenAI-compatible API of
OCI Generative AI. Install the adapter together with the ``oci`` extra, which brings the OCI request
signing used by the underlying ``openai`` client:

.. code-block:: bash

    pip install "pyagentspec[autogen,oci]"

The ``model_id``, ``compartment_id``, ``conversation_store_id``, ``retry_policy`` (``max_attempts``
and ``request_timeout``) and the ``client_config`` authentication (API key, session token, instance
principal or resource principal) of the configuration are honoured. With an
``OciClientConfigWithGenAiApiKey`` (an OCI Generative AI API key) the client sends the key as a
bearer token instead of signing requests, so the ``oci`` extra is not needed; the key is read from
the configuration or from the ``OCI_GENAI_API_KEY`` environment variable.

Limitations of the OpenAI-compatible API on AutoGen:

* only the ``ON_DEMAND`` serving mode is supported;
* Cohere models are not served by the OpenAI-compatible API, use a runtime based on the native OCI
  API (WayFlow, LangGraph) for them;
* the ``openai_responses`` API type is not supported by AutoGen, use ``openai_chat_completions``
  (or the default ``oci``).
* Meta Llama models served by OCI reject tool calling when the conversation starts with a system
  message, which is how AutoGen sends the agent's system prompt: on AutoGen, use them for agents
  without tools.
