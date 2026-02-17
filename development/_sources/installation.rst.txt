.. _installation:

Installation
============

.. only:: stable

  You can find all versions and supported platforms of |project| in the :package_index:`\ `.

  For example, if you want to install |package_name| |stable_release|:

  .. code-block:: bash
      :substitutions:

      pip install "|package_name|==|stable_release|"

  Installing with ``pip`` pulls prebuilt binary wheels on supported platforms.

  .. only:: builder_html

      The list below shows the package versions used in the CI environment, with Business Approval requests filed for each as part of the release process.
      :download:`constraints.txt <../../../pyagentspec/constraints/constraints.txt>`

      If you want to install |project| with exactly these package versions, download the file and run:

      .. code-block:: bash
          :substitutions:

          pip install "|package_name|==|stable_release|"  -c constraints.txt

.. only:: dev

  1. Clone the `repository <https://github.com/oracle/agent-spec>`_.

    .. code-block:: bash
      :substitutions:

      git clone git@github.com:oracle/agent-spec.git

  .. tip::
      If you face any problem, check with the Agent Spec team.

  Next, install PyAgentSpec directly from source.

  1. Create a fresh Python environment for building and running Agent Spec assistants:

    .. code-block:: bash
      :substitutions:

        python3.10 -m venv <venv_name>
        source <venv_name>/bin/activate

  2. Move to the *agent-spec/pyagentspec* directory:

    .. code-block:: bash
      :substitutions:

        cd agent-spec/pyagentspec

  3. Install ``pyagentspec``:

    .. code-block:: bash
      :substitutions:

        bash install-dev.sh

Extra dependencies
------------------

|project| offers optional extra dependencies that can be installed to enable additional features.

* The ``autogen`` extra dependency gives access to the AutoGen runtime adapter.
* The ``langgraph``, ``langgraph_mcp`` extra dependencies give access to the LangGraph runtime adapter.
* The ``wayflow``, ``wayflow_oci``, ``wayflow_a2a``, ``wayflow_datastore`` extra dependency gives access to the WayFlow runtime adapter.
* The ``agent-framework`` extra dependency gives access to the Microsoft Agent Framework runtime adapter.
* The ``crewai`` extra dependency gives access to the CrewAI runtime adapter. Note that this adapter might be incompatible with other adapters if installed in the same virtual environment due to conflicting dependencies.

To install extra dependencies, run the following command specifying the list of dependencies you want to install:

.. code-block:: bash
    :substitutions:

    pip install "|package_name|[extra-dep-1,extra-dep-2]==|stable_release|"

Supported platforms
-------------------

|project| strives for compatibility with major platforms and environments wherever possible.

Operating systems and CPU architectures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 50 30 30
   :header-rows: 1

   * - OS / CPU Architecture Support State
     - x86-64
     - ARM64
   * - Linux
     - Supported
     - Untested
   * - macOS
     - Supported
     - Supported


Python version
~~~~~~~~~~~~~~

How to read the table:

* Unsupported: the package or one of its dependencies is not compatible with the Python version;
* Untested: the package and its dependencies are compatible with the Python version, but they are not tested;
* Supported: the package and its dependencies are compatible with the Python version, and the package is tested on that version.

.. list-table::
   :widths: 30 30
   :header-rows: 1

   * - Python version
     - Support State
   * - Python 3.8
     - Unsupported
   * - Python 3.9
     - Unsupported
   * - Python 3.10
     - Supported
   * - Python 3.11
     - Supported
   * - Python 3.12
     - Supported
   * - Python 3.13
     - Supported
   * - Python 3.14
     - Supported


Package manager
~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 30
   :header-rows: 1

   * - Package Manager
     - Support State
   * - pip
     - Supported
   * - conda
     - Untested


Python implementation
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 30
   :header-rows: 1

   * - Implementation
     - Support
   * - CPython
     - Supported
   * - PyPy
     - Untested

What do *Supported*, *Untested* and *Unsupported* mean?

* *Unsupported*: The package or one of its dependencies is not compatible with the Python version.
* *Untested*: The package and its dependencies are compatible with the Python version, but they are not tested.
* *Supported*: The package and its dependencies are compatible with the Python version, and the package is tested on that version.
