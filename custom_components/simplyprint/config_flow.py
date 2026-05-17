from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SimplyPrintAPI, SimplyPrintAuthError, SimplyPrintConnectionError
from .const import CONF_API_KEY, CONF_COMPANY_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_COMPANY_ID): str,
    }
)


class SimplyPrintConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            company_id = user_input[CONF_COMPANY_ID].strip()

            await self.async_set_unique_id(f"{DOMAIN}_{company_id}")
            self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                api = SimplyPrintAPI(api_key, company_id, session)
                user_data = await api.get_user()
                title = (
                    user_data.get("data", {}).get("name")
                    or f"SimplyPrint ({company_id})"
                )
            except SimplyPrintAuthError:
                errors["base"] = "invalid_auth"
            except SimplyPrintConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=title,
                    data={CONF_API_KEY: api_key, CONF_COMPANY_ID: company_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
