from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.simplyprint.api import SimplyPrintAuthError, SimplyPrintConnectionError
from custom_components.simplyprint.const import CONF_API_KEY, CONF_COMPANY_ID, DOMAIN
from tests.conftest import MOCK_CONFIG

# Patch target: SimplyPrintAPI as instantiated inside the config flow module
_API_PATH = "custom_components.simplyprint.config_flow.SimplyPrintAPI"


async def _start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_shows_user_form(hass):
    result = await _start_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup_creates_entry(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(
            return_value={"data": {"name": "Acme Printers"}}
        )
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Acme Printers"
    assert result["data"][CONF_API_KEY] == MOCK_CONFIG[CONF_API_KEY]
    assert result["data"][CONF_COMPANY_ID] == MOCK_CONFIG[CONF_COMPANY_ID]


async def test_successful_setup_strips_whitespace(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "  key-with-spaces  ", CONF_COMPANY_ID: "  99  "},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "key-with-spaces"
    assert result["data"][CONF_COMPANY_ID] == "99"


async def test_invalid_auth_shows_error(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(side_effect=SimplyPrintAuthError())
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_connection_error_shows_error(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(
            side_effect=SimplyPrintConnectionError("timeout")
        )
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_unexpected_error_shows_unknown(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(side_effect=RuntimeError("boom"))
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


async def test_already_configured_aborts(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        # First setup
        result = await _start_flow(hass)
        await hass.config_entries.flow.async_configure(result["flow_id"], MOCK_CONFIG)

    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        # Second setup with the same company ID should abort
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_title_falls_back_to_company_id_when_name_missing(hass):
    with patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={})
        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert MOCK_CONFIG[CONF_COMPANY_ID] in result["title"]
