.. _top-howtoparallelflowexecution:

=====================================
How to Run Multiple Flows in Parallel
=====================================

Parallelism is a fundamental concept in computing that enables tasks to be processed concurrently,
significantly enhancing system efficiency, scalability, and overall performance.

Agent Spec supports the execution of multiple Flows in parallel, using the :ref:`ParallelFlowNode <ParallelFlowNode>`.
This guide will show you how to:

- use :ref:`ParallelFlowNode <ParallelFlowNode>` to run several tasks in parallel
- use :ref:`LlmNode <LlmNode>` to summarize the outcome of the parallel tasks

To follow this guide, you need an LLM.
Agent Spec supports several LLM API providers.
Select an LLM from the options below:

.. include:: ../_components/llm_config_tabs.rst

Basic implementation
====================

In this guide, we will create a ``Flow`` that generates a marketing message for a user.
Taking the username that identifies the user as input, we will take advantage of the ``ParallelFlowNode``
to concurrently retrieve information about the user and the context, so that we can finally generate a
personalized marketing welcome message.

We first define the following server tools that retrieve the desired information:

* One tool that retrieves the current time;
* One tool that retrieves the user information, like name and date of birth;
* One tool that gathers the user's purchase history;
* One tool that looks for the current list of items on sale, which could be recommended to the user.

.. warning::

    In ``ParallelFlowNode`` subflows, it's important to avoid calls to ClientTools, as they would require
    to temporarily pause the execution to wait for client's response. This is an operation that, based on
    the runtime implementation, might require to interrupt the execution of the flow, with undesired side
    effects on the final outcome.

.. literalinclude:: ../code_examples/howto_parallelflownode.py
    :language: python
    :start-after: .. start-##_Define_the_tools
    :end-before: .. end-##_Define_the_tools

These tools simply gather information, therefore they can be easily parallelized.
We create the flows that wrap the tools we just created, and we collect them all in a ``ParallelFlowNode``
for parallel execution. For simplicity, to create the subflows we use a helper that takes a single node
and creates a flow containing only that node, and exposing its inputs and outputs.

.. literalinclude:: ../code_examples/howto_parallelflownode.py
    :language: python
    :start-after: .. start-##_Create_the_flows_to_be_run_in_parallel
    :end-before: .. end-##_Create_the_flows_to_be_run_in_parallel

The ``ParallelFlowNode`` we created will expose all the outputs that the different inner flows generate.
We use this information to ask an LLM to generate a personalized welcome message for the user, which should also
have a marketing purpose.

.. literalinclude:: ../code_examples/howto_parallelflownode.py
    :language: python
    :start-after: .. start-##_Generate_the_marketing_message
    :end-before: .. end-##_Generate_the_marketing_message

Now that we have all the steps that compose our flow, we just put everything together to create it, and we
execute it to generate our personalized message.

.. literalinclude:: ../code_examples/howto_parallelflownode.py
    :language: python
    :start-after: .. start-##_Create_and_test_the_final_flow
    :end-before: .. end-##_Create_and_test_the_final_flow


Notes about parallelization
===========================

Not all sub-flows can be executed in parallel.
Agent Spec does not forbid specific configurations for ``ParallelFlowNode`` subflows, but there are several
precautions to take when parallelization is enabled, especially when sub-flows are supposed to access mutable
shared resources (e.g., the conversation), or interrupt the normal execution of the flow (e.g., client tools).

For more information about parallel execution support in Agent Spec, please check the :ref:`language specification <agentspecspec_nightly>`.
For guidelines about secure implementation of concurrent execution, instead, check our :ref:`security guidelines <securityconsiderations>`.


Export the Agent Spec configuration
===================================

The Agent Spec configuration is generated in JSON format.
These configurations can be loaded and executed in Agent Spec-compatible systems such as the WayFlow runtime.
See, for example, :doc:`How to Execute Agent Spec Configurations with WayFlow <howto_execute_agentspec_with_wayflow>`.

.. literalinclude:: ../code_examples/howto_parallelflownode.py
    :language: python
    :start-after: .. start-##_Export_config_to_Agent_Spec
    :end-before: .. end-##_Export_config_to_Agent_Spec

API Reference: :ref:`AgentSpecSerializer <serialize>`

Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_parallelflownode.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_parallelflownode.yaml
            :language: yaml

Recap
=====

This guide covered how to define tasks for parallel execution in Agent Spec.

.. collapse:: Below is the complete code from this guide.

    .. literalinclude:: ../code_examples/howto_parallelflownode.py
        :language: python
        :linenos:
        :start-after: .. start-##_Full_code
        :end-before: .. end-##_Full_code

Next steps
==========

Having learned how to perform generic parallel operations in Agent Spec, you may now proceed to
:doc:`How to Do Map and Reduce Operations in Flows <howto_mapnode>`.
