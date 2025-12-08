# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import TYPE_CHECKING, Any, Callable, Union

from pyagentspec._lazy_loader import LazyLoader

if TYPE_CHECKING:
    # Important: do not move this import out of the TYPE_CHECKING block so long as crewai is an optional dependency.
    # Otherwise, importing the module when they are not installed would lead to an import error.

    import crewai
    from crewai import LLM as CrewAILlm
    from crewai import Agent as CrewAIAgent
    from crewai import Flow as CrewAIFlow
    from crewai.tools import BaseTool as CrewAIBaseTool
    from crewai.tools.base_tool import Tool as CrewAITool
    from crewai.tools.structured_tool import CrewStructuredTool as CrewAIStructuredTool
else:
    crewai = LazyLoader("crewai")
    # We need to import the classes this way because it's the only one accepted by the lazy loader
    CrewAILlm = crewai.LLM
    CrewAIAgent = crewai.Agent
    CrewAIFlow = crewai.Flow
    CrewAIBaseTool = LazyLoader("crewai.tools").BaseTool
    CrewAITool = LazyLoader("crewai.tools.base_tool").Tool
    CrewAIStructuredTool = LazyLoader("crewai.tools.structured_tool").CrewStructuredTool

CrewAIComponent = Union[CrewAIAgent, CrewAIFlow[Any]]
CrewAIServerToolType = Union[CrewAITool, Callable[..., Any]]

__all__ = [
    "CrewAILlm",
    "CrewAIAgent",
    "CrewAIFlow",
    "CrewAIBaseTool",
    "CrewAITool",
    "CrewAIStructuredTool",
    "CrewAIComponent",
    "CrewAIServerToolType",
]
