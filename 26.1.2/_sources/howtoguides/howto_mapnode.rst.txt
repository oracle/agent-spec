.. _top-howtomapstep:

============================================
How to Do Map and Reduce Operations in Flows
============================================

Map-Reduce is a programming model essential for efficiently processing large datasets across distributed systems.
It is widely used in software engineering to enhance data processing speed and scalability.

Agent Spec supports the Map and Reduce operations in Flows, using the :ref:`MapNode <mapnode>`.
This guide will show you how to use :ref:`MapNode <mapnode>` to perform an operation on **all elements of a list**

.. image:: ../_static/howto/mapnode.svg
    :align: center
    :scale: 100%
    :alt: Flow diagram of a MapNode

Basic implementation
====================

Assuming you want to summarize a few articles.
You have the option to generate the summary with the :ref:`LlmNode <llmnode>` class:

.. literalinclude:: ../code_examples/howto_mapnode.py
    :language: python
    :start-after: .. start-##_Create_the_Flow_for_the_MapNode
    :end-before: .. end-##_Create_the_Flow_for_the_MapNode

This step takes a single article, and generates a summary.
Since you have a list of articles, use the ``MapNode`` class to generate a summary for each article.
Pay attention in using the right names for inputs and outputs of the ``MapNode``:
according to the Agent Spec language specification, you should prepend the ``iterated_`` prefix
to the inputs of the sub-flow that should be "mapped", and the ``collected_`` prefix to the outputs
of the sub-flow that should be "reduced".

In this case we select the ``append`` reduction method for the only subflow output we have (i.e., ``summary``).
This corresponds to the default behavior of the ``MapNode``, so we don't need to specify anything.

Please, refer to the :ref:`Agent Spec specification <agentspecspec>` for more information.

.. literalinclude:: ../code_examples/howto_mapnode.py
    :language: python
    :start-after: .. start-##_Create_the_MapNode
    :end-before: .. end-##_Create_the_MapNode

The code above will connect:

- the ``article`` input of the sub-flow to the ``iterated_article`` input of the ``MapNode``
- the ``summary`` output of the sub-flow to the ``collected_summary`` output of the ``MapNode``

Once this is done, you can create the flow for the ``MapNode``:

.. literalinclude:: ../code_examples/howto_mapnode.py
    :language: python
    :start-after: .. start-##_Create_the_final_Flow
    :end-before: .. end-##_Create_the_final_Flow

Enabling parallelization
========================

Agent Spec offers a parallel version of ``MapNode`` called ``ParallelMapNode`` : the node's behavior is
equivalent, but the map operation is supposed to be performed in parallel.
The flow we implemented for our map-reduce operation in this guide is well suited to enable parallelism,
as it does not contain criticalities, such as access to mutable resources, or input requests.
We can enable parallelism for the ``MapNode`` by simply changing the creation of the node to use the ``ParallelMapNode`` class:

.. literalinclude:: ../code_examples/howto_mapnode.py
    :language: python
    :start-after: .. start-##_Create_the_ParallelMapNode
    :end-before: .. end-##_Create_the_ParallelMapNode

Notes about parallelization
---------------------------

Not all sub-flows can be executed in parallel.
Agent Spec does not forbid specific configurations for ``ParallelMapNode`` subflows, but there are several
precautions to take when parallelization is enabled, especially when the sub-flow is supposed to access mutable
shared resources (e.g., the conversation), or interrupt the normal execution of the flow (e.g., client tools).

For more information about parallel execution support in Agent Spec, please check the :ref:`language specification <agentspecspec_nightly>`.
For guidelines about secure implementation of concurrent execution, instead, check our :ref:`security guidelines <securityconsiderations>`.


Agent Spec Serialization
========================

You can export the assistant configuration using the :ref:`AgentSpecSerializer <serialize>`.

.. literalinclude:: ../code_examples/howto_mapnode.py
    :language: python
    :start-after: .. start-export-config-to-agentspec
    :end-before: .. end-export-config-to-agentspec


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_mapnode.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_mapnode.yaml
            :language: yaml

Recap
=====

In this guide, you learned how to implement a map-reduce operation using Agent Spec components.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_mapnode.py
        :language: python
        :start-after: .. start-full-code
        :end-before: .. end-full-code

Next steps
==========

Having learned how to perform ``map`` and ``reduce`` operations in Agent Spec,
you may now proceed to :doc:`How to Build an Orchestrator-Workers Agents Pattern <howto_orchestrator_agent>`
and :doc:`How to Execute Agent Spec Across Frameworks <howto_execute_agentspec_across_frameworks>`.
