# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

try:
    import crewai
except ImportError:
    # This means that crewai is not installed. This case is already managed by the lazy loader in the public modules
    pass
except RuntimeError as e:
    # ChromaDB requires a relatively new version of SQLite which is not always supported
    # If the import fails because of that, we try to override the sqlite version with the python version of it
    # If even that is not available, we fail in the end
    if "Your system has an unsupported version of sqlite3" in str(e):
        __import__("pysqlite3")
        import sys

        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    else:
        # This is another runtime error, we raise it normally
        raise e
