# Copyright © 2025, 2026 Oracle and/or its affiliates.
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


LANGGRAPH_DEPS = [
    "langgraph>=1.0.5",
    "langchain>=1.2.0",
    "langchain-openai>=1.1.7",
    "langchain-ollama>=1.0.1",
    "anyio>=4.10.0,<4.12.0",
    "langgraph-checkpoint>=3.0.1,<4.0.0",  # To mitigate CVE-2025-64439
]


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
        "openai-agents": [
            "openai-agents>=0.6.9",
            "libcst>=1.5,<2",
        ],
        "langgraph": LANGGRAPH_DEPS,
        "langgraph_mcp": LANGGRAPH_DEPS + ["langchain-mcp-adapters"],
        "wayflow": ["wayflowcore>=25.4.3; python_version < '3.14'"],
        "wayflow_oci": ["wayflowcore[oci]>=25.4.3; python_version < '3.14'"],
        "wayflow_a2a": ["wayflowcore[a2a]>=25.4.3; python_version < '3.14'"],
        "wayflow_datastore": ["wayflowcore[datastore]>=25.4.3; python_version < '3.14'"],
        "agent-framework": [
            "agent-framework>=1.0.0b260130; python_version < '3.14'",
            "agent-framework-core>=1.0.0b260130; python_version < '3.14'",
        ],
    },
)
