from typing import Any

from pydantic import BaseModel, Field


class PresenceExtraInfo(BaseModel):
    id: int = Field(alias="Id")
    label: str = Field(alias="Label")
    # PATCHED for HA vendoring: upstream used builtin `any` as annotation
    values: Any = Field(alias="Values")

    class Config:
        arbitrary_types_allowed = True
