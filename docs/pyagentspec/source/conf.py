# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import json
import logging

# -- Project information -----------------------------------------------------
import os
import sys
from pathlib import Path

from sphinx.application import Sphinx

import pyagentspec

sys.path.insert(0, os.path.abspath("_ext"))
logging.basicConfig(level=logging.INFO)

project = "PyAgentSpec"
package_name = "pyagentspec"
copyright = "2025, Oracle and/or its affiliates."
author = "Oracle Labs"

html_static_path = ["_static"]

# The last stable release we want users to install
with open(Path(__file__).parents[3] / "VERSION", "r") as f:
    version_file = f.read().strip()

# The IDE complains, but the tags set exists
# We add stable as current version, we might add the version switch in the future
tags.add("stable")  # type: ignore

# The short X.Y version.
version = ".".join(pyagentspec.__version__.split(".")[:2])

# The full version, including alpha/beta/rc tags.
release = pyagentspec.__version__

# Use STABLE_RELEASE if it's set, otherwise use version_file
stable_release = os.getenv("STABLE_RELEASE") or version_file
if stable_release is None:
    raise Exception("Error: STABLE_RELEASE environment variable is not set.")

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx_substitution_extensions",
    "sphinx.ext.extlinks",
    "sphinx_toolbox.collapse",
    "sphinx_tabs.tabs",
    "sphinx.ext.doctest",
    "sphinx_copybutton",
    "copy_sidebar_ext",  # custom extension in _ext/copy_sidebar_ext.py
    "process_docstring_ext",  # custom extension in _ext/process_docstring_ext.py
    "docstring_role_ext",  # is used to support the :docstring: role
    "generate_api_table_ext",  # is used to automatically generate the API table
]

# Set the variables that should be replaced in the substitution-extensions directives
rst_prolog = f"""
.. |release| replace:: {release}
.. |stable_release| replace:: {stable_release}
.. |author| replace:: {author}
.. |copyright| replace:: {copyright}
.. |project| replace:: {project}
.. |package_name| replace:: {package_name}
"""

extlinks = {
    "package_index": (
        f"https://pypi.org/simple/{package_name}/%s",
        "Package Index %s",
    ),
    "issue": ("https://github.com/oracle/agent-spec/issues/%s", "issue "),
    "pr": ("https://github.com/oracle/agent-spec/pull/%s", "PR #"),
}


source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

autodoc_default_options = {
    "members": True,
    "inherited-members": False,
    "show-inheritance": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Use __init__ method docstring.
# autoclass_content = "both"

# Add type hints to parameter description, not to signature.
autodoc_typehints = "description"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of builtin themes.


html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "WayFlow GitHub repository",
            "url": "https://github.com/oracle/agent-spec",
            "icon": "_static/icons/github-icon.svg",
            "type": "local",
        },
    ],
    "show_toc_level": 1,
    "header_links_before_dropdown": 4,
    "navbar_align": "left",
    "show_prev_next": False,
    "pygments_light_style": "xcode",  # for light mode
    "pygments_dark_style": "monokai",  # for dark mode
    "navbar_align": "left",
    "navbar_start": ["navbar-logo"],
    "navbar_center": [
        "navbar-new"
    ],  # Custom top navigation - defined in the template, navbar-new.html, in the _templates dir.
    "logo": {
        "image_light": "_static/agentspec-dark.svg",
        "image_dark": "_static/agentspec-white.svg",
    },
}

html_sidebars = {
    "**": ["sidebar-nav-bs"],
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_css_files = ["css-style.css", "core.css"]
html_favicon = "_static/favicon.svg"

# to remove the `View page source` link
html_show_sourcelink = False

# -- Options for Copy button -------------------------------------------------
# Remove >>> and ... prompts from code blocks
# https://sphinx-copybutton.readthedocs.io/en/latest/use.html#using-regexp-prompt-identifiers
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
# enables the copy prevention of the above patterns when they match.
copybutton_prompt_is_regexp = True


def autodoc_skip_member(app: Sphinx, what, name, obj, skip, options):
    """
    Skips showing an attribute as a member if it is already in the list of parameters.
    This prevents duplicated fields in Pydantic / dataclasses.
    """
    if what == "class" and "annotations" in app.env.temp_data:
        annotations = list(app.env.temp_data["annotations"].values())[0]
        if name in annotations:
            return True
    return skip


def setup(app: Sphinx):
    app.connect("autodoc-skip-member", autodoc_skip_member)
    app.add_js_file("js/fix-navigation.js")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
