# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module and its submodules define all the Agent Spec components and utilities."""

from importlib.metadata import version

import pyagentspec.flows.edges  # noqa: F401
import pyagentspec.flows.nodes  # noqa: F401
import pyagentspec.llms  # noqa: F401
import pyagentspec.tools  # noqa: F401

from ._swarm import Swarm
from .agent import Agent
from .component import Component
from .ociagent import OciAgent
from .openaiagent import OpenAiAgent
from .property import Property
from .serialization import AgentSpecDeserializer, AgentSpecSerializer

__all__ = [
    "AgentSpecDeserializer",
    "AgentSpecSerializer",
    "Property",
    "Component",
    "Agent",
    "OpenAiAgent",
    "OciAgent",
    "Swarm",
]
# Get the version from the information set in the setup of this package
__version__ = version("pyagentspec")
