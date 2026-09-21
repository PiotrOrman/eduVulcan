from typing import Any

from pydantic import BaseModel, Field

from ._subject import Subject


class GradeAverage(BaseModel):
    id: int = Field(alias="Id")
    pupil_id: int = Field(alias="PupilId")
    period_id: int = Field(alias="PupilId")
    subject: Subject = Field(alias="Subject")
    average: str | None = Field(alias="Average")
    points: str | None = Field(alias="Points")
    # PATCHED for HA vendoring: upstream used builtin `any` as annotation
    annotation: Any = Field(alias="Annotation")
    scope: str = Field(alias="Scope")

    class Config:
        arbitrary_types_allowed = True
