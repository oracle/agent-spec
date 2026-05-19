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
    # 3rd party dependencies (imported in code)
    "langgraph>=1.2.0,<1.3.0",
    "langchain-core>=1.4.0,<1.5.0",
    "langchain>=1.3.1,<1.4.0",
    "langchain-openai>=1.2.1,<1.3.0",
    "langchain-ollama>=1.0.1",
    "anyio>=4.10.0,<4.12.0",
    "httpx>0.28.0",
    "langgraph-swarm>=0.1.0",
    # 4rth party dependencies
    "certifi>=2025.1.31",  # needed to avoid CVE present in earlier versions
    "langgraph-checkpoint>=4.0.1,<5.0.0",  # needed to avoid CVE present in earlier versions
    "langsmith>=0.8.0,<1.0.0",  # needed to avoid CVE present in earlier versions
    "urllib3>=2.7.0",  # needed to avoid CVE present in earlier versions
]

LANGGRAPH_FULL_DEPS = LANGGRAPH_DEPS + [
    # 3rd party dependencies (imported in code)
    "langchain-mcp-adapters>=0.2.2",
    "langchain-oci>=0.2.6",
    # 4rth party dependencies
    "cryptography>=46.0.7",  # needed to avoid CVE present in earlier versions
    "pyOpenSSL>=26.0.0,<27.0.0",  # needed to avoid CVE present in earlier versions
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
        # 3rd party dependencies (imported in code)
        "jsonschema>=4.23.0,<5",
        "pydantic>=2.12.5,<2.14",
        "pyyaml>=6,<7",
        "typing-extensions>=4.15.0",
    ],
    test_suite="tests",
    entry_points={
        "console_scripts": [],
    },
    include_package_data=True,
    extras_require={
        "autogen": [
            # 3rd party dependencies (imported in code)
            "autogen-core>=0.5.6; python_version < '3.13'",
            "autogen-ext[ollama,openai]>=0.5.6; python_version < '3.13'",
            "autogen-agentchat>=0.5.6; python_version < '3.13'",
            "httpx>0.28.0; python_version < '3.13'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.13'",  # needed to avoid CVE present in earlier versions
            "urllib3>=2.7.0; python_version < '3.13'",  # needed to avoid CVE present in earlier versions
        ],
        "openai-agents": [
            # 3rd party dependencies (imported in code)
            "openai-agents>=0.6.9",
            "libcst>=1.5,<2",
            "httpx>0.28.0",
            # 4rth party dependencies
            "certifi>=2025.1.31",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7",  # needed to avoid CVE present in earlier versions
            "urllib3>=2.7.0",  # needed to avoid CVE present in earlier versions
        ],
        "crewai": [
            # 3rd party dependencies (imported in code)
            "crewai[litellm]>=1.6.1; python_version < '3.14'",
            "httpx>0.28.0; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            # litellm is included to fix CVEs
            "litellm>=1.84.0,<1.85.0; python_version < '3.14'",
            "urllib3>=2.7.0; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "langgraph": LANGGRAPH_DEPS,
        "langgraph-full": LANGGRAPH_FULL_DEPS,
        # wayflowcore 26.1.x caps starlette<0.48.0, so use the fixed
        # WayFlow dev release until a compatible stable release is published.
        "wayflow": [
            # 3rd party dependencies (imported in code)
            "wayflowcore>=26.2.0.dev3; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "wayflow_oci": [
            # 3rd party dependencies (imported in code)
            "wayflowcore[oci]>=26.2.0.dev3; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "pyOpenSSL>=26.0.0,<27.0.0; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "urllib3>=2.7.0; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "wayflow_a2a": [
            # 3rd party dependencies (imported in code)
            "wayflowcore[a2a]>=26.2.0.dev3; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "wayflow_datastore": [
            # 3rd party dependencies (imported in code)
            "wayflowcore[datastore]>=26.2.0.dev3; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "agent-framework": [
            # 3rd party dependencies (imported in code)
            "agent-framework>=1.0.0b260130; python_version < '3.14'",
            "httpx>0.28.0; python_version < '3.14'",
            # 4rth party dependencies
            "certifi>=2025.1.31; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
            # including otel-semconv-ai to address internal agent-framework bug
            "opentelemetry-semantic-conventions-ai<0.4.14",
            "urllib3>=2.7.0; python_version < '3.14'",  # needed to avoid CVE present in earlier versions
        ],
        "evaluation": [
            # 3rd party dependencies (imported in code)
            "anyio>=4.10.0,<4.12.0",
            "litellm>=1.84.0,<1.85.0; python_version < '3.14'",
            "pandas>=2.3.0,<3.0.0",
            "oci>=2.158.2",
            "numpy>=2.2.6",
            # 4rth party dependencies
            "certifi>=2025.1.31",  # needed to avoid CVE present in earlier versions
            "cryptography>=46.0.7",  # needed to avoid CVE present in earlier versions
            "pyOpenSSL>=26.0.0,<27.0.0",  # needed to avoid CVE present in earlier versions
            "urllib3>=2.7.0",  # needed to avoid CVE present in earlier versions
        ],
    },
)
