.. _wayflowadapter:

=============================
Agent Spec Adapters - WayFlow
=============================


.. figure:: ../../_static/icons/wayflow-adapter.jpg
    :align: center
    :scale: 18%
    :alt: Agent Spec adapter for WayFlow

    ↑ With the **Agent Spec adapter for WayFlow**, you can easily import agents from external frameworks using Agent Spec and run them with WayFlow.


*WayFlow is the reference framework for Agent Spec, provides modular components for developing AI-powered assistants,
supporting both workflow-based and agent-style applications.*


Get started
===========

To get started, set up your Python environment (Python 3.10 or newer required),
and then install the PyAgentSpec package as well as WayFlowCore.


.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install pyagentspec wayflowcore


Usage Examples
==============

You are now ready to use the adapter to:

.. toctree::
   :maxdepth: 1

   Run Agent Spec configurations with WayFlow <spec_to_wayflow>
   Convert WayFlow agents to Agent Spec <wayflow_to_spec>
