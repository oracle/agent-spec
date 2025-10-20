# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import importlib
import inspect

from docutils import nodes
from sphinx.util.docutils import SphinxRole


class DocstringRole(SphinxRole):
    def run(self):
        try:
            # The text argument contains the path
            full_path = self.text
            # print(f"Processing: {full_path}")  # Debug print

            # Parse the full path
            module_path, obj_name = full_path.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)
            obj = getattr(module, obj_name)

            # Get docstring based on whether it's a class or function
            if inspect.isclass(obj):
                # For classes, try class docstring first, then __init__ docstring
                docstring = obj.__doc__
                if not docstring:
                    docstring = getattr(obj.__init__, "__doc__", None)
            else:
                # For functions, get the function docstring
                docstring = obj.__doc__

            # Handle case where no docstring is found
            if not docstring:
                return [nodes.Text("No documentation available")], []

            # Get first line of docstring
            docstring = docstring.strip().split("\n")[0]
            return [nodes.Text(docstring)], []

        except Exception as e:
            print(f"Error processing {full_path}: {str(e)}")  # Debug print
            return [nodes.Text(f"Error getting docstring: {e}")], []


def setup(app):
    app.add_role("docstring", DocstringRole())
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
