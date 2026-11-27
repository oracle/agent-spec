.. _spectoopenai:

Run Agent Spec configurations with OpenAI Agents
================================================

This usage example showcases the creation of a simple Agent Spec Agent, subsequently serialized into JSON
and converted into an OpenAI Agents assistant. Also includes mapping of a `ServerTool` and execution of the conversation.

.. literalinclude:: ../../code_examples/adapter_openai_quickstart.py
    :language: python
    :start-after: .. start-agentspec_to_runtime
    :end-before: .. end-agentspec_to_runtime


OCI Generative AI models
------------------------

Agents whose ``llm_config`` is an ``OciGenAiConfig`` run on OCI Generative AI through its
OpenAI-compatible API. Install the adapter together with the ``oci`` extra, which provides the
OCI request signing:

.. code-block:: bash

    pip install "pyagentspec[openai-agents,oci]"

The adapter honours the ``model_id``, ``compartment_id``, ``conversation_store_id`` and
``retry_policy`` (mapped to the client retries and timeout) of the configuration, and the four
``client_config`` authentication types (API key, session token, instance principal and resource
principal). With an ``OciClientConfigWithGenAiApiKey`` (an OCI Generative AI API key) the client
sends the key as a bearer token instead of signing requests, so the ``oci`` extra is not needed;
the key is read from the configuration or from the ``OCI_GENAI_API_KEY`` environment variable.
The ``api_type`` selects the SDK model: ``openai_responses`` gives an
``OpenAIResponsesModel``, any other value an ``OpenAIChatCompletionsModel``.

Limitations of the OpenAI-compatible API of OCI Generative AI:

* Cohere models are only served by the native OCI API (use the WayFlow or LangGraph runtimes);
* the ``DEDICATED`` serving mode is not supported;
* the Responses API requires an OpenAI model, or a ``conversation_store_id`` for other models;
* Llama models reject tool calls when the conversation starts with a system message, so agents
  with a ``system_prompt`` and tools cannot use Llama models through this API; they also send
  tool arguments as strings, which tool implementations must accept.

Flow code generation references models by name only and cannot carry the OCI client
configuration, so Flows containing agents with an ``OciGenAiConfig`` are rejected with an
explicit error; load such agents as components instead.
