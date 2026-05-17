from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SimplyPrintAPI, SimplyPrintConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SimplyPrintCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: SimplyPrintAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            spools, printers = await asyncio.gather(
                self.api.get_filament(),
                self.api.get_printers(),
            )
            return {
                "spools": {s["id"]: s for s in spools if "id" in s},
                "printers": {p["id"]: p for p in printers if "id" in p},
            }
        except SimplyPrintConnectionError as err:
            raise UpdateFailed(f"SimplyPrint API error: {err}") from err
