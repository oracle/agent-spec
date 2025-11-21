# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module and its submodules define all the Agent Spec components and utilities."""

from importlib.metadata import version

import pyagentspec.flows  # noqa: F401
import pyagentspec.llms  # noqa: F401
import pyagentspec.mcp  # noqa: F401
import pyagentspec.tools  # noqa: F401

# We import the registry to make sure to import all the Component classes
from ._component_registry import BUILTIN_CLASS_MAP as _BUILTIN_CLASS_MAP
from ._openaiagent import OpenAiAgent
from .a2aagent import A2AAgent, A2AConnectionConfig, A2ASessionParameters
from .agent import Agent
from .component import Component
from .managerworkers import ManagerWorkers
from .ociagent import OciAgent
from .property import Property
from .serialization import AgentSpecDeserializer, AgentSpecSerializer
from .swarm import Swarm

__all__ = [
    "A2AAgent",
    "A2AConnectionConfig",
    "A2ASessionParameters",
    "AgentSpecDeserializer",
    "AgentSpecSerializer",
    "Property",
    "Component",
    "Agent",
    "OpenAiAgent",
    "OciAgent",
    "Swarm",
    "ManagerWorkers",
]
# Get the version from the information set in the setup of this package
__version__ = version("pyagentspec")
