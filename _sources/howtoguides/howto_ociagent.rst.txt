.. _top-howtoociagent:

===================================
How to Use OCI Generative AI Agents
===================================

`OCI GenAI Agents <https://www.oracle.com/artificial-intelligence/generative-ai/agents>`_ is a service
to create agents in the OCI console. These agents are defined remotely, including their tools, prompts,
and optional documents for retrieval-augmented generation (RAG), and can be used for inference.

In this guide, you will learn how to use an OCI agent in Agent Spec using the :ref:`OciAgent <ociagent>`
class from the ``pyagentspec`` package.


Basic usage
===========

To get started, first create your OCI GenAI Agent in the OCI Console.
Consult the `OCI documentation <https://docs.oracle.com/en-us/iaas/Content/generative-ai-agents/home.htm>`_ for detailed steps.

Next, create an ``OciClientConfig`` object to configure the connection to the OCI service.
See the :doc:`OCI LLM configuration <howto_llm_from_different_providers>` for detailed instructions how to configure this object.

You will also need the ``agent_endpoint_id`` from the OCI Console.
This ID points to the agent you want to connect to, while the client configuration is about connecting to the entire service.

Once these are in place, you can create your agent in a few lines:

.. literalinclude:: ../code_examples/howto_ociagent.py
    :language: python
    :start-after: .. start-##_Creating_the_agent
    :end-before: .. end-##_Creating_the_agent

Note that the ``OciAgent`` is an extension of ``RemoteAgent`` in Agent Spec, which is considered an ``AgenticComponent``.
It follows that OCI agents can be used in ``AgentNodes`` inside Agent Spec flows.

Recap
=====

This how-to guide covered how to define an OCI Generative AI Agent in Agent Spec.

.. collapse:: Below is the complete code from this guide.

  .. literalinclude:: ../code_examples/howto_ociagent.py
    :language: python
    :linenos:
    :start-after: .. start-##_Creating_the_agent
    :end-before: .. end-##_Creating_the_agent

Next steps
==========

Now that you have learned how to use OCI agents in `WayFlow <https://github.com/oracle/wayflow>`_,
you may proceed to :doc:`How to Use Agents in Flows <howto_orchestrator_agent>`.
