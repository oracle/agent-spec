# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines helpers for Agent Spec components."""
import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from pyagentspec import Property

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
