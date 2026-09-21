"""Sensors for the eduVULCAN integration.

Per pupil: next lesson (with today's/tomorrow's plan in attributes,
substitutions included), homework count, upcoming exams count and the
lucky number.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import EduVulcanConfigEntry
from .const import DOMAIN, MANUFACTURER
from .coordinator import EduVulcanCoordinator, PupilData
from .iris.models import Schedule

# ScheduleChange.type semantics (per Wulkanowy/hebe conventions):
# 1 = lesson cancelled, 2 = substitution, 3 = rescheduled, 4 = class merged.
CHANGE_CANCELLED = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EduVulcanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eduVULCAN sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []
    for pupil_id in coordinator.data:
        entities.extend(
            [
                NextLessonSensor(coordinator, entry, pupil_id),
                HomeworkSensor(coordinator, entry, pupil_id),
                ExamsSensor(coordinator, entry, pupil_id),
                LuckyNumberSensor(coordinator, entry, pupil_id),
            ]
        )
    async_add_entities(entities)


def _lesson_is_cancelled(lesson: Schedule) -> bool:
    sub = lesson.substitution
    return bool(
        sub
        and (
            sub.class_absence
            or (sub.change and sub.change.type == CHANGE_CANCELLED)
        )
    )


def _lesson_change_description(lesson: Schedule) -> str | None:
    """Human-readable substitution/change info, if any."""
    sub = lesson.substitution
    if not sub:
        return None
    if _lesson_is_cancelled(lesson):
        return sub.reason or "odwołane"
    parts: list[str] = []
    if sub.subject and lesson.subject and sub.subject.name != lesson.subject.name:
        parts.append(f"przedmiot: {sub.subject.name}")
    if sub.teacher_primary:
        parts.append(f"zastępstwo: {sub.teacher_primary.display_name}")
    if sub.room and lesson.room and sub.room.code != lesson.room.code:
        parts.append(f"sala: {sub.room.code}")
    if sub.reason:
        parts.append(sub.reason)
    return ", ".join(parts) if parts else "zmiana"


def _effective_subject(lesson: Schedule) -> str:
    sub = lesson.substitution
    if sub and sub.subject:
        return sub.subject.name
    if lesson.subject:
        return lesson.subject.name
    return lesson.event or "?"


def _effective_room(lesson: Schedule) -> str | None:
    sub = lesson.substitution
    if sub and sub.room:
        return sub.room.code
    if lesson.room:
        return lesson.room.code
    return None


def _effective_teacher(lesson: Schedule) -> str | None:
    sub = lesson.substitution
    if sub and sub.teacher_primary:
        return sub.teacher_primary.display_name
    if lesson.teacher_primary:
        return lesson.teacher_primary.display_name
    return None


def _lesson_to_dict(lesson: Schedule) -> dict[str, Any]:
    return {
        "nr": lesson.time_slot.position,
        "od": lesson.time_slot.start.strftime("%H:%M"),
        "do": lesson.time_slot.end.strftime("%H:%M"),
        "przedmiot": _effective_subject(lesson),
        "sala": _effective_room(lesson),
        "nauczyciel": _effective_teacher(lesson),
        "odwolane": _lesson_is_cancelled(lesson),
        "zmiana": _lesson_change_description(lesson),
    }


def _lesson_start(lesson: Schedule) -> datetime:
    naive = datetime.combine(lesson.date_, lesson.time_slot.start)
    return naive.replace(tzinfo=dt_util.get_default_time_zone())


def _day_plan(schedule: list[Schedule], day: date) -> list[dict[str, Any]]:
    lessons = [lesson for lesson in schedule if lesson.date_ == day]
    lessons.sort(key=lambda lesson: lesson.time_slot.position)
    return [_lesson_to_dict(lesson) for lesson in lessons]


class EduVulcanEntity(CoordinatorEntity[EduVulcanCoordinator], SensorEntity):
    """Base entity: one device per pupil."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EduVulcanCoordinator,
        entry: EduVulcanConfigEntry,
        pupil_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._pupil_id = pupil_id
        pupil = coordinator.data[pupil_id].account.pupil
        unit = coordinator.data[pupil_id].account.unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{pupil_id}")},
            name=f"Szkoła {pupil.first_name}",
            manufacturer=MANUFACTURER,
            model=unit.display_name,
        )

    @property
    def pupil_data(self) -> PupilData:
        return self.coordinator.data[self._pupil_id]


class NextLessonSensor(EduVulcanEntity):
    """Next (not cancelled) lesson; full today/tomorrow plan in attributes."""

    _attr_translation_key = "next_lesson"
    _attr_icon = "mdi:school"

    def __init__(
        self,
        coordinator: EduVulcanCoordinator,
        entry: EduVulcanConfigEntry,
        pupil_id: int,
    ) -> None:
        super().__init__(coordinator, entry, pupil_id)
        self._attr_unique_id = f"{entry.entry_id}_{pupil_id}_next_lesson"

    def _next_lesson(self) -> Schedule | None:
        now = dt_util.now()
        upcoming = [
            lesson
            for lesson in self.pupil_data.schedule
            if not _lesson_is_cancelled(lesson) and _lesson_start(lesson) >= now
        ]
        if not upcoming:
            return None
        return min(upcoming, key=_lesson_start)

    @property
    def native_value(self) -> str:
        lesson = self._next_lesson()
        if lesson is None:
            return "brak lekcji"
        start = _lesson_start(lesson)
        prefix = "" if start.date() == dt_util.now().date() else f"{start:%a} "
        return f"{_effective_subject(lesson)} ({prefix}{start:%H:%M})"

    def _next_school_day(self, after: date) -> date | None:
        """First day after `after` that has any (not cancelled) lesson."""
        days = sorted(
            {
                lesson.date_
                for lesson in self.pupil_data.schedule
                if lesson.date_ > after and not _lesson_is_cancelled(lesson)
            }
        )
        return days[0] if days else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        lesson = self._next_lesson()
        next_day = self._next_school_day(today)
        return {
            "nastepna_lekcja_start": (
                _lesson_start(lesson).isoformat() if lesson else None
            ),
            "nastepna_lekcja_sala": _effective_room(lesson) if lesson else None,
            "dzis": _day_plan(self.pupil_data.schedule, today),
            "jutro": _day_plan(self.pupil_data.schedule, today + timedelta(days=1)),
            "nastepny_dzien_szkolny": next_day.isoformat() if next_day else None,
            "nastepny_dzien_szkolny_plan": (
                _day_plan(self.pupil_data.schedule, next_day) if next_day else []
            ),
        }


class HomeworkSensor(EduVulcanEntity):
    """Number of homework items with a deadline today or later."""

    _attr_translation_key = "homework"
    _attr_icon = "mdi:book-edit"

    def __init__(
        self,
        coordinator: EduVulcanCoordinator,
        entry: EduVulcanConfigEntry,
        pupil_id: int,
    ) -> None:
        super().__init__(coordinator, entry, pupil_id)
        self._attr_unique_id = f"{entry.entry_id}_{pupil_id}_homework"

    def _open_homework(self):
        today = dt_util.now().date()
        items = [hw for hw in self.pupil_data.homework if hw.deadline >= today]
        items.sort(key=lambda hw: hw.deadline)
        return items

    @property
    def native_value(self) -> int:
        return len(self._open_homework())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        return {
            "zadania": [
                {
                    "przedmiot": hw.subject.name,
                    "tresc": hw.content,
                    "termin": hw.deadline.isoformat(),
                    "dni_do_terminu": (hw.deadline - today).days,
                    "wymaga_odpowiedzi": hw.is_answer_required,
                }
                for hw in self._open_homework()
            ]
        }


class ExamsSensor(EduVulcanEntity):
    """Number of upcoming exams/tests."""

    _attr_translation_key = "exams"
    _attr_icon = "mdi:clipboard-text"

    def __init__(
        self,
        coordinator: EduVulcanCoordinator,
        entry: EduVulcanConfigEntry,
        pupil_id: int,
    ) -> None:
        super().__init__(coordinator, entry, pupil_id)
        self._attr_unique_id = f"{entry.entry_id}_{pupil_id}_exams"

    def _upcoming_exams(self):
        today = dt_util.now().date()
        items = [ex for ex in self.pupil_data.exams if ex.deadline.date() >= today]
        items.sort(key=lambda ex: ex.deadline)
        return items

    @property
    def native_value(self) -> int:
        return len(self._upcoming_exams())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        return {
            "sprawdziany": [
                {
                    "przedmiot": ex.subject.name,
                    "typ": ex.type,
                    "tresc": ex.content,
                    "data": ex.deadline.date().isoformat(),
                    "dni_do": (ex.deadline.date() - today).days,
                }
                for ex in self._upcoming_exams()
            ]
        }


class LuckyNumberSensor(EduVulcanEntity):
    """Today's lucky number at school."""

    _attr_translation_key = "lucky_number"
    _attr_icon = "mdi:clover"

    def __init__(
        self,
        coordinator: EduVulcanCoordinator,
        entry: EduVulcanConfigEntry,
        pupil_id: int,
    ) -> None:
        super().__init__(coordinator, entry, pupil_id)
        self._attr_unique_id = f"{entry.entry_id}_{pupil_id}_lucky_number"

    @property
    def native_value(self) -> int | None:
        return self.pupil_data.lucky_number

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pupil = self.pupil_data.account.pupil
        journal = self.pupil_data.account.journal
        return {
            "numer_w_dzienniku": journal.pupil_number if journal else None,
            "trafiony": (
                journal is not None
                and self.pupil_data.lucky_number is not None
                and journal.pupil_number == self.pupil_data.lucky_number
            ),
            "uczen": f"{pupil.first_name} {pupil.surname}",
        }
