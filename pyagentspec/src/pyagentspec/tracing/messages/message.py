# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Optional

from pydantic import BaseModel


class Message(BaseModel):
    """Model used to specify LLM message details in events and spans"""

    id: Optional[str] = None
    "Identifier of the message"

    content: str
    "Content of the message"

    sender: Optional[str] = None
    "Sender of the message"

    role: str
    "Role of the sender of the message. Typically 'user', 'assistant', or 'system'"
