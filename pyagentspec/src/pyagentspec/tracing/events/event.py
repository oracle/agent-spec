# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import time
import uuid
from typing import Any, Optional

from pydantic import Field

from pyagentspec.tracing._basemodel import BaseModelWithSensitiveInfo


class Event(BaseModelWithSensitiveInfo):

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """A unique identifier for the event"""
    name: Optional[str] = None
    """The name of the event. If None, the event class name is used."""
    description: str = ""
    """The description of the event."""
    timestamp: int = Field(default_factory=time.time_ns)
    """The timestamp of when the event occurred"""
    metadata: dict[str, Any] = Field(default_factory=dict)
    """Metadata related to the event"""

    def model_post_init(self, __context: Any) -> None:
        """Set the default name if it is not provided."""
        super().model_post_init(__context)
        if not self.name:
            self.name = self.__class__.__name__
