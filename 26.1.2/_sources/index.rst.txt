.. _landing_page:

:orphan:

Open Agent Specification, Agent Spec
====================================

.. container:: gradient-background

   .. container:: description

      Open Agent Specification (Agent Spec) is a portable language for defining agentic
      systems. It defines building blocks for standalone agents and structured agentic workflows as well
      as common ways of composing them into multi-agent systems.

   .. container:: description-second link-style

      A portable, platform-agnostic configuration language for more reliable agents and agentic systems.

.. container:: button-group

      :doc:`Get Started <installation>`
      :doc:`Documentation <docs_home>`

.. container:: quickstart-container margin_top

  .. rubric:: Why Agent Spec?
    :class: sub-title

  .. container:: benefits

    .. container:: benefit-card card-blue

      .. image:: _static/img/01-flexibility.svg
          :class: benefit-icon
          :alt: Flexible

      **Flexible**
      Agent Spec lets you focus on designing an agentic solution — ranging from single agents
      to multi-agent systems and tailored structured flows — ensuring a strong fit for your needs.

    .. container:: benefit-card card-blue

      .. image:: _static/img/02-reliable-consistent.svg
          :class: benefit-icon
          :alt: Reliable & Consistent

      **Reliable & Consistent**
      With Agent Spec, each agent follows an explicit specification, promoting uniform behavior across
      frameworks and increasing confidence in important workflows.


    .. container:: benefit-card card-blue

      .. image:: _static/img/03-extensible.svg
          :class: benefit-icon
          :alt: Extensible

      **Extensible**
      Agent Spec is designed to be extensible, allowing developers to define custom components to meet
      their specific needs. This flexibility lets Agent Spec adapt to a wide range of requirements.

    .. container:: benefit-card card-blue

      .. image:: _static/img/04-modular-reusable.svg
          :class: benefit-icon
          :alt: Modular & Reusable

      **Modular & Reusable**
      Agent Spec’s component-based design lets agents and flows be developed independently, then mixed and
      matched like building blocks, making reuse and composition into complex assistants faster and simpler.

    .. container:: benefit-card card-blue

      .. image:: _static/img/05-cross-frame-portal.svg
          :class: benefit-icon
          :alt: Portable Across Frameworks

      **Portable Across Frameworks**
      Author agents once and run them with any compatible runtime. Agent Spec decouples
      design from execution, helping deliver more predictable behavior across frameworks.

    .. container:: benefit-card card-blue

      .. image:: _static/img/06-evaluation.svg
          :class: benefit-icon
          :alt: Evaluation-Ready

      **Evaluation-Ready**
      By defining agents with a standardized representation, Agent Spec is designed to streamline
      testing and side-by-side comparisons on frameworks that support the specifications.


.. container:: positioning-container margin_top

  .. rubric:: Agent Spec Positioning
    :class: sub-title

  .. container:: positioning

    .. container:: detail-card card-blue fullwidth

      .. container:: md-6

        .. image:: _static/agentspec_spec_img/agentspec_positioning.svg
          :class: hiw-icon
          :alt: Agent Spec complements other standardizations, such as MCP or A2A

      .. container:: md-6


        .. rubric:: How does Agent Spec fits the modern Agentic Ecosystem
            :class: detail-title

        Agent Spec aims to streamline the architecture and design of agentic assistants
        and workflows, serving as an intermediate representation that abstracts away
        implementation details of specific agentic frameworks.

        While protocols like MCP and A2A standardize tool or resource provisioning
        as well as inter-agent communication, Agent Spec complements these efforts by
        enabling standardized configuration of components related to agentic system design and execution in general.

        ㅤ➔ :doc:`Learn more about Agent Spec in the agentic ecosystem <agentspec/positioning>`


.. container:: quickstart-container

  .. rubric:: Agent Spec Components
    :class: sub-title

  .. container:: details

    .. container:: detail-card card-blue

      .. image:: _static/_images/agent-ai.svg
          :class: hiw-icon
          :alt: Agents

      .. rubric:: Agents
        :class: detail-title

      Agents are LLM-powered assistants that can converse with users, use external tools,
      and cooperate with other agents, autonomously managing their processes and strategies
      to flexibly achieve assigned tasks.

      ㅤ➔ :doc:`Build Your First Agent <howtoguides/howto_execute_agentspec_with_wayflow>`

    .. container:: detail-card card-blue

      .. image:: _static/_images/flow-ai.svg
          :class: hiw-icon
          :alt: Flows

      .. rubric:: Flows
        :class: detail-title

      Flows are structured assistants composed of connected nodes that form coherent action sequences.
      Each node performs a specific function, supporting controllable and efficient execution of business
      processes and tasks.

      ㅤ➔ :doc:`Build Your First Flow <howtoguides/howto_flow_with_conditional_branches>`


  .. rubric:: Using Agent Spec
    :class: sub-title

  .. container:: details

    .. container:: detail-card card-blue

      .. rubric:: PyAgentSpec
        :class: detail-title

      PyAgentSpec is an SDK designed to create agents in Python that conform to the
      Agent Spec spec and generate their configuration as JSON or YAML.

      ㅤ➔ :doc:`Build your first Flow using PyAgentSpec <howtoguides/howto_flow_with_conditional_branches>`

    .. container:: detail-card card-blue

      .. rubric:: Agent Spec Runtimes
        :class: detail-title

      Agent Spec configurations can be executed with Agent Spec-compatible runtimes,
      such as `WayFlow <https://github.com/oracle/wayflow>`_, or
      with other agentic frameworks, like AutoGen, CrewAI, and LangGraph, through adapters.

      ㅤ➔ :doc:`Run your Agent Spec Configuration Across Frameworks <howtoguides/howto_execute_agentspec_across_frameworks>`


.. container:: quickstart-container

  .. rubric:: Quick Start
      :class: sub-title

  .. only:: stable

    .. container:: qs-content

      To install `pyagentspec`, run:

      .. code-block:: bash
        :substitutions:

        pip install "|package_name|==|stable_release|"

  .. only:: dev

    .. container:: qs-content

      To install the development version of `pyagentspec` from source, run:

      .. code-block:: bash
        :substitutions:

        bash install-dev.sh


  For a complete list of supported Python versions and platforms, see the :doc:`installation guide <installation>`.

.. container:: ainext-container

    .. rubric:: Explore the Documentation
        :class: sub-title

    .. container:: wnext

      .. container:: wnext-card

        .. raw:: html

            <a href="howtoguides/index.html" class="benefit-card-link">

      .. container:: wn-card-content card-blue

        .. image:: _static/img/examples.svg
            :class: benefit-icon
            :alt: How-to Guides

        **How-to Guides**

        Goal-oriented guides with self-contained code examples to help you complete specific tasks.

      .. raw:: html

          </a>

      .. container:: wnext-card

        .. raw:: html

            <a href="api/index.html" class="benefit-card-link">

      .. container:: wn-card-content card-blue

        .. image:: _static/img/exploring.svg
            :class: benefit-icon
            :alt: Explore the API docs

        **API Documentation**

        Dive deeper into the API documentation to explore the classes, methods, and functions available in the library.

      .. raw:: html

          </a>

      .. container:: wnext-card

        .. raw:: html

            <a href="agentspec/index.html" class="benefit-card-link">

      .. container:: wn-card-content card-blue

        .. image:: _static/img/language_spec.svg
            :class: benefit-icon
            :alt: Read the language specification

        **Language specification**

        Give a look at the latest version of the Agent Spec configuration language specification.

      .. raw:: html

          </a>


.. toctree::
  :maxdepth: 3
  :hidden:

  Open Agent Spec <docs_home>
