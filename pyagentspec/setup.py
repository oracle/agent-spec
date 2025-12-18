# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import io
import os.path

from setuptools import find_packages, setup

NAME = "pyagentspec"

# Check for an environment variable to override the version
VERSION = os.environ.get("BUILD_VERSION")
if not VERSION:
    with open("../VERSION") as version_file:
        VERSION = version_file.read().strip()


def read(file_name):
    """Read a text file and return the content as a string."""
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with io.open(file_path, encoding="utf-8") as f:
        return f.read()


setup(
    name=NAME,
    version=VERSION,
    description="Package defining the PyAgentSpec library for Agents and LLM fixed-flows abstractions.",
    license="Apache-2.0 OR UPL-1.0",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="",
    author="Oracle",
    author_email="",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="NLP, text generation,code generation, LLM, Assistant, Tool, Agent",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.10",
    install_requires=[
        "jsonschema>=4.23.0,<5",
        "pydantic>=2.10,<2.13",
        "pyyaml>=6,<7",
        "httpx>0.28.0",
        "urllib3>=2.5.0",  # needed to avoid a CVE present on earlier versions
    ],
    test_suite="tests",
    entry_points={
        "console_scripts": [],
    },
    include_package_data=True,
    extras_require={
        "autogen": [
            "autogen-core>=0.5.6; python_version < '3.13'",
            "autogen-ext[ollama,openai]>=0.5.6; python_version < '3.13'",
            "autogen-agentchat>=0.5.6; python_version < '3.13'",
        ],
        "langgraph": [
            "langgraph>=0.5.3,<1.0.0",
            "langchain-core>=0.3,<1.0.0",
            "langchain-openai>=0.3.7",
            "langchain-ollama>=0.3.3",
            "langgraph-checkpoint>=3.0.1,<4.0.0" # To mitigate CVE-2025-64439
        ],
    },
)
