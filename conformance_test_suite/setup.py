# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import io
import os.path

from setuptools import find_packages, setup

NAME = "agentspec-cts-sdk"

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
    description=(
        "Interfaces and protocols for the implementation "
        "of AgentSpec Conformance Test Suite compatible runtimes."
    ),
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
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Dependent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="NLP, text generation, code generation, LLM, Assistant, Tool, Agent",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    install_requires=[
        "fastapi[standard]",
        "mcp>=1.24.0,<2.0.0",
        "pytest>=7.0",
        "pytest-timeout>=2.4.0",
        "allure-pytest>=2.13.5",
        "sqlalchemy>=2.0.40",
        "oracledb>=2.2.0",
        "psycopg2-binary>=2.9.11",
    ],
    test_suite="tests",
    entry_points={
        "console_scripts": [],
    },
    include_package_data=True,
)
