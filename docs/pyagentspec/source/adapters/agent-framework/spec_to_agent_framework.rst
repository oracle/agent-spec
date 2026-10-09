.. _spectoagentframework:

Run Agent Spec configurations with Microsoft Agent Framework
============================================================

This usage example showcases the creation of a simple Agent Spec Agent, subsequently serialized into JSON and converted into a
Microsoft Agent Framework assistant. Also includes mapping of a ``ServerTool`` and execution of the conversation.

.. literalinclude:: ../../code_examples/adapter_agent_framework_quickstart.py
    :language: python
    :start-after: .. start-agentspec_to_runtime
    :end-before: .. end-agentspec_to_runtime

OCI Generative AI models
------------------------

An ``OciGenAiConfig`` is executed through the OpenAI-compatible API of OCI Generative AI:
the adapter builds an ``openai`` client that signs every request with the OCI credentials of the
``client_config`` (API key, session token, instance principal or resource principal) and targets
the configured compartment. This requires the ``oci-genai-auth`` package:

.. code-block:: bash

    pip install "pyagentspec[agent-framework,oci]"

With an ``OciClientConfigWithGenAiApiKey`` (an OCI Generative AI API key), the client sends the key
as a bearer token instead: no request signing and no ``oci-genai-auth`` package are needed. The key
is read from the configuration or from the ``OCI_GENAI_API_KEY`` environment variable.

The ``api_type`` selects the Agent Framework client: ``oci`` and ``openai_chat_completions`` map
to ``OpenAIChatCompletionClient``, ``openai_responses`` to ``OpenAIChatClient``. The ``model_id``,
``compartment_id``, ``conversation_store_id`` and ``retry_policy`` (client retries and request
timeout) are honoured; ``default_generation_parameters`` apply at the agent level as for the other
LLM configurations.

Limitations of the OpenAI-compatible API of OCI Generative AI:

* Cohere models and the ``DEDICATED`` serving mode are not served by this API; use a runtime
  based on the native OCI API (WayFlow, LangGraph) for them.
* The Responses API accepts OpenAI models only, unless a ``conversation_store_id`` is configured.
  Without a conversation store the service does not retain responses, so agents send the whole
  conversation at every turn instead of chaining them with ``previous_response_id``.
* Meta models require the conversation to start with a user message when tools are bound, while
  Agent Framework sends the agent instructions first; use them without tools, or use OpenAI models
  for tool-calling agents.
