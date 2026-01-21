.. _top-catchexception:

================================
How to Catch Exceptions in Flows
================================

Exception handling is essential for building robust and reliable flows.
It allows a system to gracefully handle unexpected issues (e.g., bad inputs, unavailable resources)
without crashing, while still producing useful outputs or routing to recovery logic.

In Agent Spec, you can implement exception handling using the :ref:`CatchExceptionNode <catchexceptionnode>`.
This node runs a subflow and, if an error occurs, transitions to a dedicated branch
(``caught_exception_branch``) and exposes a ``caught_exception_info`` output.

This guide will show you how to:

1. Define a subflow that may raise an exception
2. Wrap the subflow with :ref:`CatchExceptionNode <catchexceptionnode>`
3. Export the configuration using :ref:`AgentSpecSerializer <serialize>`

Basic implementation
====================

There are many reasons why a part of a Flow can raise an exception. For instance,
a tool can be missing some inputs, or running the tool failed, or an LLM call failed
on a long completion or raised an error due to guardrails. For all those cases and more,
using a ``CatchExceptionNode`` is the way to catch and control the recovery of the flow
execution when such exceptions are raised.

In the configuration below, we wrap a subflow that may fail with ``CatchExceptionNode``.
When an exception occurs, the node uses the ``caught_exception_branch`` to transition to
the next step.

.. literalinclude:: ../code_examples/howto_catchexception.py
    :language: python
    :start-after: .. start-##_Define_flaky_tool
    :end-before: .. end-##_Define_flaky_tool

Here some simplicity we use a tool which we know is potentially flaky, but the errors
could be coming from other components (e.g., failures in LLM calls, calls to remote APIs, etc).

.. literalinclude:: ../code_examples/howto_catchexception.py
    :language: python
    :start-after: .. start-##_Define_subflow
    :end-before: .. end-##_Define_subflow

To use the ``CatchExceptionNode``, a subflow must be created to encapsulate the flow
to catch exceptions of.

.. literalinclude:: ../code_examples/howto_catchexception.py
    :language: python
    :start-after: .. start-##_Wrap_with_CatchExceptionNode
    :end-before: .. end-##_Wrap_with_CatchExceptionNode

This subflow is then passed to the ``CatchExceptionNode``.

.. literalinclude:: ../code_examples/howto_catchexception.py
    :language: python
    :start-after: .. start-##_Build_Exception_Handling_Flow
    :end-before: .. end-##_Build_Exception_Handling_Flow

When the subflow raises an error, the ``CatchExceptionNode`` takes a separate branch.
This enables different actions depending on whether the subflow successfully completed or
failed in its execution.

Agent Spec Serialization
========================

You can export the configuration to Agent Spec JSON using the :ref:`AgentSpecSerializer <serialize>`.
The resulting configuration can be loaded and executed by Agent Spec-compatible runtimes.

.. literalinclude:: ../code_examples/howto_catchexception.py
    :language: python
    :start-after: .. start-##_Export_config_to_Agent_Spec
    :end-before: .. end-##_Export_config_to_Agent_Spec


Here is what the **Agent Spec representation will look like ↓**

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_catchexception.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_catchexception.yaml
            :language: yaml


Notes
=====

- ``caught_exception_info`` defaults to ``null`` when no exception is raised.
- Ensure subflow outputs have defaults if you rely on them in exception paths.
- Do not expose security-sensitive information in ``caught_exception_info``.

Recap
=====

This guide covered how to add exception handling to Agent Spec flows by:

- Wrapping a subflow with :ref:`CatchExceptionNode <catchexceptionnode>`
- Routing on the exception path using :ref:`BranchingNode <branchingnode>`
- Exporting the final configuration with :ref:`AgentSpecSerializer <serialize>`

Next steps
==========

Having learned how to handle exceptions in flows, you may now proceed to:

- :doc:`Develop a Flow with Conditional Branches <howto_flow_with_conditional_branches>`
- :doc:`Run Multiple Flows in Parallel <howto_parallelflownode>`
- :doc:`Do Map and Reduce Operations in Flows <howto_mapnode>`
