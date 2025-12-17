# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict

from pydantic import BaseModel

from pyagentspec.sensitive_field import is_sensitive_field
from pyagentspec.serialization.serializationcontext import _SerializationContextImpl
from pyagentspec.versioning import AgentSpecVersionEnum

_PII_MASK = "** MASKED **"


class _TracingSerializationContextImpl(_SerializationContextImpl):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.agentspec_version = AgentSpecVersionEnum.current_version


class BaseModelWithSensitiveInfo(BaseModel):

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Serialize a Pydantic Component masking sensitive information.

        Is invoked upon a ``model_dump`` call.
        """
        mask_sensitive_information = kwargs.pop("mask_sensitive_information", True)
        if "context" not in kwargs:
            kwargs["context"] = _TracingSerializationContextImpl()
        serialized_model_dict = super().model_dump(*args, **kwargs)
        for field_name, field_info in self.__class__.model_fields.items():
            if field_name in serialized_model_dict:
                if getattr(field_info, "exclude", False):
                    serialized_model_dict.pop(field_name)
                elif mask_sensitive_information and is_sensitive_field(field_info):
                    serialized_model_dict[field_name] = _PII_MASK
        serialized_model_dict["type"] = self.__class__.__name__
        return serialized_model_dict
