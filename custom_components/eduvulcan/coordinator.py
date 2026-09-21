"""Data update coordinator for the eduVULCAN integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    EXAMS_DAYS_AHEAD,
    HOMEWORK_DAYS_AHEAD,
    SCHEDULE_DAYS_AHEAD,
)
from .iris._exceptions import IrisApiException
from .iris.api import IrisHebeCeApi
from .iris.models import Account, Exam, Homework, Schedule

_LOGGER = logging.getLogger(__name__)


@dataclass
class PupilData:
    """Snapshot of one pupil's school data."""

    account: Account
    schedule: list[Schedule] = field(default_factory=list)
    homework: list[Homework] = field(default_factory=list)
    exams: list[Exam] = field(default_factory=list)
    lucky_number: int | None = None


class EduVulcanCoordinator(DataUpdateCoordinator[dict[int, PupilData]]):
    """Fetches data for all pupils on the registered eduVULCAN account."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: IrisHebeCeApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.api = api

    async def async_close(self) -> None:
        """Release the underlying aiohttp session."""
        await self.api._http.close()  # noqa: SLF001 (vendored lib has no public close)

    async def _async_update_data(self) -> dict[int, PupilData]:
        today = date.today()
        try:
            accounts = await self.api.get_accounts()
        except IrisApiException as err:
            raise UpdateFailed(f"eduVULCAN: cannot fetch account list: {err}") from err

        data: dict[int, PupilData] = {}
        for account in accounts:
            pupil_id = account.pupil.id
            rest_url = account.unit.rest_url
            pupil_data = PupilData(account=account)

            try:
                pupil_data.schedule = await self.api.get_schedule(
                    rest_url=rest_url,
                    pupil_id=pupil_id,
                    date_from=today,
                    date_to=today + timedelta(days=SCHEDULE_DAYS_AHEAD),
                )
                pupil_data.homework = await self.api.get_homework(
                    rest_url=rest_url,
                    pupil_id=pupil_id,
                    date_from=today - timedelta(days=7),
                    date_to=today + timedelta(days=HOMEWORK_DAYS_AHEAD),
                )
                pupil_data.exams = await self.api.get_exams(
                    rest_url=rest_url,
                    pupil_id=pupil_id,
                    date_from=today,
                    date_to=today + timedelta(days=EXAMS_DAYS_AHEAD),
                )
            except IrisApiException as err:
                raise UpdateFailed(
                    f"eduVULCAN: fetch failed for pupil {pupil_id}: {err}"
                ) from err

            # Lucky number is nice-to-have; don't fail the whole update on it.
            try:
                lucky = await self.api.get_lucky_number(
                    rest_url=rest_url,
                    pupil_id=pupil_id,
                    constituent_unit_id=account.constituent_unit.id,
                    day=today,
                )
                pupil_data.lucky_number = lucky.number
            except IrisApiException:
                _LOGGER.debug(
                    "Lucky number unavailable for pupil %s", pupil_id, exc_info=True
                )

            data[pupil_id] = pupil_data

        if not data:
            raise UpdateFailed("eduVULCAN: account list is empty")

        return data
