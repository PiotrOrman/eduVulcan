from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ._clazz import Clazz
from ._distribution import Distribution
from ._employee import Employee
from ._presence_type import PresenceType
from ._subject import Subject
from ._timeslot import Timeslot


class Lesson(BaseModel):
    lesson_id: int = Field(alias="LessonId")
    presence_type: PresenceType | None = Field(alias="PresenceType")
    # PATCHED for HA vendoring: upstream used builtin `any` as annotation
    collection: list[Any] = Field(alias="Collection")
    justification_status: int | None = Field(alias="JustificationStatus")
    id: int = Field(alias="Id")
    lesson_class_id: int = Field(alias="LessonClassId")
    day: date = Field(alias="DayAt")
    calculate_presence: bool = Field(alias="CalculatePresence")
    group_definition: str | None = Field(alias="GroupDefinition")
    public_resources: str | None = Field(alias="PublicResources")
    remote_resources: str | None = Field(alias="RemoteResources")
    replacement: bool = Field(alias="Replacement")
    modified_at: datetime = Field(alias="ModifiedAt")
    global_key: str = Field(alias="GlobalKey")
    note: str | None = Field(alias="Note")
    topic: str | None = Field(alias="Topic")
    lesson_number: int | None = Field(alias="LessonNumber")
    lesson_class_global_key: str = Field(alias="LessonClassGlobalKey")
    time_slot: Timeslot = Field(alias="TimeSlot")
    subject: Subject | None = Field(alias="Subject")
    teacher_primary: Employee = Field(alias="TeacherPrimary")
    teacher_secondary: Employee | None = Field(alias="TeacherSecondary")
    teacher_mod: Employee = Field(alias="TeacherMod")
    clazz: Clazz = Field(alias="Clazz")
    distribution: Distribution | None = Field(alias="Distribution")
    # PATCHED for HA vendoring: upstream used builtin `any` as annotation
    didactics: Any = Field(alias="Didactics")

    class Config:
        arbitrary_types_allowed = True
