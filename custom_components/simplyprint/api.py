from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


class SimplyPrintAuthError(Exception):
    pass


class SimplyPrintConnectionError(Exception):
    pass


class SimplyPrintAPI:
    def __init__(
        self,
        api_key: str,
        company_id: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._api_key = api_key
        self._company_id = company_id
        self._session = session
        self._base = f"{BASE_URL}/{company_id}"

    async def _post(self, route: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base}/{route}"
        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }
        try:
            async with self._session.post(
                url, json=data or {}, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 401:
                    raise SimplyPrintAuthError("Invalid API key")
                resp.raise_for_status()
                return await resp.json()
        except SimplyPrintAuthError:
            raise
        except aiohttp.ClientResponseError as err:
            raise SimplyPrintConnectionError(f"HTTP {err.status}: {err.message}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SimplyPrintConnectionError(f"Connection error: {err}") from err

    async def get_user(self) -> dict[str, Any]:
        return await self._post("account/GetUser")

    async def get_filament(self) -> list[dict[str, Any]]:
        result = await self._post("filament/GetFilament")
        # Response may nest data under various keys
        for key in ("data", "filament", "spools"):
            if key in result and isinstance(result[key], list):
                return result[key]
        return []

    async def get_printers(self) -> list[dict[str, Any]]:
        result = await self._post("printers/Get")
        for key in ("data", "printers"):
            if key in result and isinstance(result[key], list):
                return result[key]
        return []

    async def get_filament_locations(self) -> list[dict[str, Any]]:
        result = await self._post("filament/locations/GetList")
        for key in ("data", "locations"):
            if key in result and isinstance(result[key], list):
                return result[key]
        return []

    async def assign_filament(
        self,
        filament_id: int,
        printer_id: int,
        extruder: int = 0,
    ) -> dict[str, Any]:
        return await self._post(
            "filament/Assign",
            {
                "filament": {str(filament_id): {"nozzle": 0, "extruder": extruder}},
                "printer_id": printer_id,
            },
        )

    async def unassign_filament(self, printer_id: int) -> dict[str, Any]:
        return await self._post("filament/Unassign", {"printer_id": printer_id})

    async def adjust_weight(self, filament_id: int, weight: float) -> dict[str, Any]:
        return await self._post("filament/AdjustWeight", {"id": filament_id, "weight": weight})

    async def mark_dried(self, filament_id: int) -> dict[str, Any]:
        return await self._post("filament/MarkDried", {"id": filament_id})

    async def assign_nfc(self, filament_id: int, nfc_id: str) -> dict[str, Any]:
        return await self._post("filament/AssignNfc", {"id": filament_id, "nfc_id": nfc_id})

    async def get_nfc_spool_flashing_data(self, filament_id: int) -> dict[str, Any]:
        return await self._post("nfc/GetSpoolFlashingData", {"id": filament_id})
