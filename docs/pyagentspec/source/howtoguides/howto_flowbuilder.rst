=====================================
Build Flows with the Flow Builder
=====================================

.. admonition:: Prerequisites

    This guide assumes you are familiar with the following concepts:

    - :ref:`Flows <flow>` and basic nodes/edges
    - Selecting an LLM configuration


Overview
========

The ``FlowBuilder`` provides a concise, readable way to assemble flows without manually wiring every edge. It supports:

- ``add_sequential``: add nodes in order and wire control edges between consecutive nodes.
- ``set_entry_point`` and ``set_finish_points``: declare the flow entry and terminal points.
- ``set_conditional``: branch to different destinations based on a source node output.
- ``build_linear_flow``: a convenience method to assemble a linear flow in one line.

See the full API in :doc:`API › Flows <../api/flows>` and quick snippets in the :ref:`Reference Sheet <flowbuilder_ref_sheet>`.


1. Build a linear flow
======================

Create two LLM nodes and connect them linearly with a single call.

.. literalinclude:: ../code_examples/howto_flowbuilder.py
    :language: python
    :start-after: .. start-##_Build_a_linear_flow
    :end-before: .. end-##_Build_a_linear_flow

API Reference: :ref:`FlowBuilder <flowbuilder>`


2. Add a conditional branch
===========================

Add a branching step where a node output (for example ``decision``) determines which node to run next. You can also define multiple finish points.

.. literalinclude:: ../code_examples/howto_flowbuilder.py
    :language: python
    :start-after: .. start-##_Build_a_flow_with_a_conditional
    :end-before: .. end-##_Build_a_flow_with_a_conditional

Notes:

- ``set_conditional`` accepts the branch key as a string output name (e.g., ``"decision"``) or as a tuple ``(node_or_name, output_name)``.
- ``set_finish_points`` declares which nodes connect to automatically created ``EndNode``(s).


3. Export the flow
==================

Serialize your flow to Agent Spec JSON for execution in a compatible runtime.

.. literalinclude:: ../code_examples/howto_flowbuilder.py
    :language: python
    :start-after: .. start-##_Export_to_IR
    :end-before: .. end-##_Export_to_IR

API Reference: :ref:`AgentSpecSerializer <serialize>`


Here is what the Agent Spec representation will look like ↓
-----------------------------------------------------------

.. collapse:: Click here to see the assistant configuration.

   .. tabs::

      .. tab:: JSON

         .. literalinclude:: ../agentspec_config_examples/howto_flowbuilder.json
            :language: json

      .. tab:: YAML

         .. literalinclude:: ../agentspec_config_examples/howto_flowbuilder.yaml
            :language: yaml


Recap
=====

This how-to guide showed how to:

- Build a linear flow in one line with ``build_linear_flow``
- Add a conditional branch with ``set_conditional``
- Declare entry and finish points and serialize your flow


Next steps
==========

- Explore more patterns in the :ref:`Reference Sheet <flowbuilder_ref_sheet>`
- See the complete API in :doc:`API › Flows <../api/flows>`
- Learn about branching and loops in :doc:`How to Develop a Flow with Conditional Branches <howto_flow_with_conditional_branches>`
