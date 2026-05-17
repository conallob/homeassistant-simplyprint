from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SimplyPrintAPI
from .const import (
    ATTR_EXTRUDER,
    ATTR_PRINTER_ID,
    ATTR_SPOOL_ID,
    ATTR_WEIGHT,
    CONF_API_KEY,
    CONF_COMPANY_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADJUST_WEIGHT,
    SERVICE_ASSIGN_FILAMENT,
    SERVICE_MARK_DRIED,
    SERVICE_UNASSIGN_FILAMENT,
)
from .coordinator import SimplyPrintCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = SimplyPrintAPI(
        entry.data[CONF_API_KEY],
        entry.data[CONF_COMPANY_ID],
        session,
    )
    coordinator = SimplyPrintCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_register_services(
    hass: HomeAssistant, coordinator: SimplyPrintCoordinator
) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ASSIGN_FILAMENT):
        return

    async def handle_assign_filament(call: ServiceCall) -> None:
        await coordinator.api.assign_filament(
            filament_id=call.data[ATTR_SPOOL_ID],
            printer_id=call.data[ATTR_PRINTER_ID],
            extruder=call.data.get(ATTR_EXTRUDER, 0),
        )
        await coordinator.async_request_refresh()

    async def handle_unassign_filament(call: ServiceCall) -> None:
        await coordinator.api.unassign_filament(
            printer_id=call.data[ATTR_PRINTER_ID],
        )
        await coordinator.async_request_refresh()

    async def handle_adjust_weight(call: ServiceCall) -> None:
        await coordinator.api.adjust_weight(
            filament_id=call.data[ATTR_SPOOL_ID],
            weight=call.data[ATTR_WEIGHT],
        )
        await coordinator.async_request_refresh()

    async def handle_mark_dried(call: ServiceCall) -> None:
        await coordinator.api.mark_dried(filament_id=call.data[ATTR_SPOOL_ID])
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSIGN_FILAMENT,
        handle_assign_filament,
        schema=vol.Schema(
            {
                vol.Required(ATTR_SPOOL_ID): cv.positive_int,
                vol.Required(ATTR_PRINTER_ID): cv.positive_int,
                vol.Optional(ATTR_EXTRUDER, default=0): vol.All(int, vol.Range(min=0)),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UNASSIGN_FILAMENT,
        handle_unassign_filament,
        schema=vol.Schema({vol.Required(ATTR_PRINTER_ID): cv.positive_int}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADJUST_WEIGHT,
        handle_adjust_weight,
        schema=vol.Schema(
            {
                vol.Required(ATTR_SPOOL_ID): cv.positive_int,
                vol.Required(ATTR_WEIGHT): vol.All(
                    vol.Coerce(float), vol.Range(min=0)
                ),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_DRIED,
        handle_mark_dried,
        schema=vol.Schema({vol.Required(ATTR_SPOOL_ID): cv.positive_int}),
    )
