How to Use Summarization Transforms
====================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :ref:`Agent <agent>`
    - :ref:`MessageTransform <messagetransform>`
    - :ref:`Datastore <datastore>`


Overview
========

Agent Spec supports **Summarization Transforms** that help manage long conversations and large messages by automatically summarizing content before it reaches the LLM. This prevents context window limits and improves efficiency.

There are two types of summarization transforms:

- :ref:`MessageSummarizationTransform <messagesummarizationtransform>`: Summarizes individual messages that exceed a specified character limit
- :ref:`ConversationSummarizationTransform <conversationsummarizationtransform>`: Summarizes conversation history when the total number of messages exceeds a threshold

.. note::
    By default, summarization transforms use an in-memory datastore for caching summarized content. You can specify your own datastore by providing a ``Datastore`` parameter. For information on how to configure different types of datastores such as :ref:`Oracle <oracledatabasedatastore>` or :ref:`PostgreSQL <postgresdatabasedatastore>`, see :doc:`How to Use Datastores <howto_datastores>`.

This guide will walk you through:

1. Configuring an LLM for summarization
2. Creating message summarization transforms
3. Creating conversation summarization transforms
4. Using transforms in agents
5. Serializing agents with transforms

Basic implementation
====================

1. Configure an LLM for summarization
--------------------------------------

Summarization transforms summarize messages or conversations before they are passed to the LLM to reduce the context size of the agent LLM. To perform the summarization, they require an LLM configuration.

.. literalinclude:: ../code_examples/howto_summarization_transforms.py
    :language: python
    :start-after: .. define-llm-config
    :end-before: .. start-transforms

API Reference: :ref:`OpenAiConfig <openaiconfig>`

2. Create summarization transforms
----------------------------------

In this section, we will create both transforms with appropriate thresholds and instructions.

.. literalinclude:: ../code_examples/howto_summarization_transforms.py
    :language: python
    :start-after: .. start-transforms
    :end-before: .. end-transforms

API Reference: :ref:`MessageSummarizationTransform <messagesummarizationtransform>`, :ref:`ConversationSummarizationTransform <conversationsummarizationtransform>`


3. Use transforms in agents
---------------------------

Add summarization transforms to agents to automatically handle long content.

.. literalinclude:: ../code_examples/howto_summarization_transforms.py
    :language: python
    :start-after: .. start-agent-with-transforms
    :end-before: .. end-agent-with-transforms

API Reference: :ref:`Agent <agent>`

4. Serializing agents with transforms
-------------------------------------

:ref:`MessageTransform <messagetransform>` configurations can be serialized to JSON or YAML for deployment.

.. literalinclude:: ../code_examples/howto_summarization_transforms.py
    :language: python
    :start-after: .. start-serialization
    :end-before: .. end-serialization

API Reference: :ref:`AgentSpecSerializer <serialize>`

Here is what the **serialized agent with transforms will look like ↓**

.. collapse:: Click here to see the agent configuration.

   .. literalinclude:: ../agentspec_config_examples/howto_summarization_transforms.json
      :language: json


Recap
=====

This guide covered how to implement summarization transforms in Agent Spec to handle long conversations and messages efficiently.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_summarization_transforms.py
        :language: python
        :linenos:
