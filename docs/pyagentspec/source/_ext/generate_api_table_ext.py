# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

import json
import logging
import os

from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# module‐level “globals” for backup
orig_api_index_existed = False
orig_api_index_content = None
# -------------------------------------------------------------------

BASE_API_INDEX_FILE_CONTENT = """.. _apireferencelanding:

.. THIS FILE IS GENERATED AUTOMATICALLY, PLEASE DO NOT MODIFY

API Reference
=============

On this page, you will find the ``pyagentspec`` API reference, ordered by component.

Click on the components and section names to access the complete API documentation pages.


"""


def generate_api_index(app):
    """
    1) Back up the existing index.rst (if any)
    2) Generate your new API index.rst
    """
    global orig_api_index_existed, orig_api_index_content

    try:
        src_dir = app.confdir  # docs/source
        api_dir = os.path.join(src_dir, "api")
        index_path = os.path.join(api_dir, "index.rst")

        # --- 1) backup ---
        if os.path.exists(index_path):
            orig_api_index_existed = True
            with open(index_path, "r", encoding="utf-8") as f:
                orig_api_index_content = f.read()
        else:
            orig_api_index_existed = False
            orig_api_index_content = None

        # --- 2) generate ---
        with open(os.path.join(src_dir, "_components/all_components.json")) as f:
            all_components = json.load(f)

        newlines = []
        for component_info in all_components:
            section_title = f":doc:`{component_info['name']} <{component_info['path']}>`"
            newlines.append(f"{section_title}\n{'-'*len(section_title)}\n")

            classes_content = component_info["classes"]
            if classes_content:

                classes_elements = [
                    (
                        f":class:`{elt['name']} <{elt['path']}>`"
                        if "name" in elt
                        else f":class:`{elt['path']}`"
                    )
                    for elt in classes_content
                ]
                docstring_elements = [f":docstring:`{elt['path']}`" for elt in classes_content]

                classes_width = max([len(x) for x in classes_elements])
                docstrings_width = max([len(x) for x in docstring_elements])

                newlines.append(f"**Classes**\n\n")
                newlines.append(f"{'='*classes_width} {'='*docstrings_width}\n")
                newlines.extend(
                    [
                        f"{cls_elt}{' '*(1+classes_width-len(cls_elt))}{doc_elt}\n"
                        for cls_elt, doc_elt in zip(classes_elements, docstring_elements)
                    ]
                )
                newlines.append(f"{'='*classes_width} {'='*docstrings_width}\n")

        newlines.append("\n.. toctree::\n   :maxdepth: 2\n   :hidden:\n")
        newlines.extend(
            [
                f"   {component_info['name']} <{component_info['path']}>"
                for component_info in all_components
            ]
        )

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(BASE_API_INDEX_FILE_CONTENT + "\n".join(newlines))

        logger.info(f"[autoapi] generated {index_path!r}")
    except Exception as e:
        print(e)
        import traceback

        print(traceback.format_exc())
        raise e


def restore_api_index(app, exception):
    """
    After the build is done (even if it failed),
    restore the original file (or delete it if it didn't exist).
    """
    src = app.confdir
    api_dir = os.path.join(src, "api")
    index = os.path.join(api_dir, "index.rst")

    # only act if we actually once ran generate_api_index
    global orig_api_index_existed, orig_api_index_content

    if orig_api_index_existed:
        # overwrite with original content
        with open(index, "w", encoding="utf-8") as f:
            f.write(orig_api_index_content or "")
        logger.info(f"[autoapi] restored original {index!r}")
    else:
        # we created it ourselves, so remove it
        try:
            os.remove(index)
            logger.info(f"[autoapi] removed generated {index!r}")
        except OSError:
            pass


def setup(app: Sphinx):
    app.connect("builder-inited", generate_api_index)
    app.connect("build-finished", restore_api_index)
    app.add_js_file("js/fix-navigation.js")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
