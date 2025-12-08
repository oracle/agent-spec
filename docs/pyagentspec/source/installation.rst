.. _installation:

Installation
============

You can find all versions and supported platforms of |project| in the :package_index:`\ `.

To install version |package_name| |stable_release|, run:

.. code-block:: bash
    :substitutions:

    pip install "|package_name|==|stable_release|"

Installing with ``pip`` pulls prebuilt binary wheels on supported platforms.

.. only:: builder_html

    The list of package versions used in the internal CI is available at:
    :download:`constraints.txt <../../../pyagentspec/constraints/constraints.txt>`

    To install |project| using these exact versions, download the file and run:

    .. code-block:: bash
        :substitutions:

        pip install "|package_name|==|stable_release|" -c constraints.txt

Extra dependencies
------------------

|project| offers optional extra dependencies that can be installed to enable additional features.

* The ``crewai`` extra dependency gives access to the CrewAI runtime adapter.

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
