"""The eduVULCAN integration.

Pulls kids' timetable, homework, exams and the lucky number from the
eduVULCAN (hebeCE) mobile API via a vendored copy of the `iris` library.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CREDENTIAL
from .coordinator import EduVulcanCoordinator
from .iris.api import IrisHebeCeApi
from .iris.credentials import RsaCredential

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type EduVulcanConfigEntry = ConfigEntry[EduVulcanCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EduVulcanConfigEntry) -> bool:
    """Set up eduVULCAN from a config entry."""
    credential = RsaCredential.model_validate_json(entry.data[CONF_CREDENTIAL])
    api = IrisHebeCeApi(credential)

    coordinator = EduVulcanCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EduVulcanConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_close()
    return unload_ok
