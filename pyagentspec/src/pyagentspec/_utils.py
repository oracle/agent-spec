# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines helpers for Agent Spec components."""
import warnings
from typing import Any, Dict, List, Type, TypeVar

from pydantic import BaseModel

from pyagentspec.serialization.pydanticdeserializationplugin import (
    PydanticComponentDeserializationPlugin,
)
from pyagentspec.serialization.pydanticserializationplugin import (
    PydanticComponentSerializationPlugin,
)

ComponentTypeT = TypeVar("ComponentTypeT", bound=Type[BaseModel])


def beta(cls: ComponentTypeT) -> ComponentTypeT:
    """
    Annotate a class as beta.

    Raise warning the first time a class is instantiated
    to inform the user the class may undergo significant changes.

    """
    original_init = cls.__init__
    is_first_instance = True

    def modified_init(self: ComponentTypeT, *args: List[Any], **kwargs: Dict[str, Any]) -> None:
        nonlocal is_first_instance
        if is_first_instance:
            warnings.warn(
                f"The {cls.__name__} class is currently in beta and may undergo significant "
                "changes or improvements. Please use it with caution.",
                UserWarning,
                stacklevel=2,
            )
            is_first_instance = False
        original_init(self, *args, **kwargs)  # type: ignore

    cls.__init__ = modified_init  # type: ignore
    return cls


class BetaComponentSerializationPlugin(PydanticComponentSerializationPlugin):
    """Serialization plugin for beta Components."""

    def __init__(self, _allow_partial_model_serialization: bool = False) -> None:
        from pyagentspec._openaiagent import OpenAiAgent

        super().__init__(
            component_types_and_models={
                component_class.__name__: component_class for component_class in (OpenAiAgent,)
            },
            _allow_partial_model_serialization=_allow_partial_model_serialization,
        )


class BetaComponentDeserializationPlugin(PydanticComponentDeserializationPlugin):
    """Deserialization plugin for beta Components."""

    def __init__(self) -> None:
        from pyagentspec._openaiagent import OpenAiAgent

        super().__init__(
            component_types_and_models={
                component_class.__name__: component_class for component_class in (OpenAiAgent,)
            }
        )
