from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.simplyprint.api import SimplyPrintAuthError, SimplyPrintConnectionError
from custom_components.simplyprint.config_flow import SimplyPrintConfigFlow
from custom_components.simplyprint.const import CONF_API_KEY, CONF_COMPANY_ID, DOMAIN
from tests.conftest import MOCK_CONFIG

_API_PATH = "custom_components.simplyprint.config_flow.SimplyPrintAPI"
_SESSION_PATH = "custom_components.simplyprint.config_flow.async_get_clientsession"


def _make_flow():
    """Return a SimplyPrintConfigFlow with all HA base-class side-effects mocked."""
    flow = SimplyPrintConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"source": "user"}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(
        side_effect=lambda title, data: {
            "type": FlowResultType.CREATE_ENTRY,
            "title": title,
            "data": data,
        }
    )
    flow.async_show_form = MagicMock(
        side_effect=lambda *, step_id, data_schema=None, errors=None, **_: {
            "type": FlowResultType.FORM,
            "step_id": step_id,
            "errors": errors or {},
        }
    )
    return flow


async def test_shows_user_form():
    flow = _make_flow()
    result = await flow.async_step_user(None)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup_creates_entry():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(
            return_value={"data": {"name": "Acme Printers"}}
        )
        result = await flow.async_step_user(MOCK_CONFIG)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Acme Printers"
    assert result["data"][CONF_API_KEY] == MOCK_CONFIG[CONF_API_KEY]
    assert result["data"][CONF_COMPANY_ID] == MOCK_CONFIG[CONF_COMPANY_ID]


async def test_successful_setup_strips_whitespace():
    flow = _make_flow()
    padded = {CONF_API_KEY: "  key-with-spaces  ", CONF_COMPANY_ID: "  99  "}
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        result = await flow.async_step_user(padded)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "key-with-spaces"
    assert result["data"][CONF_COMPANY_ID] == "99"


async def test_invalid_auth_shows_error():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(side_effect=SimplyPrintAuthError())
        result = await flow.async_step_user(MOCK_CONFIG)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_connection_error_shows_error():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(
            side_effect=SimplyPrintConnectionError("timeout")
        )
        result = await flow.async_step_user(MOCK_CONFIG)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_unexpected_error_shows_unknown():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(side_effect=RuntimeError("boom"))
        result = await flow.async_step_user(MOCK_CONFIG)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


async def test_unique_id_is_set_on_success():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        await flow.async_step_user(MOCK_CONFIG)

    flow.async_set_unique_id.assert_called_once_with(
        f"{DOMAIN}_{MOCK_CONFIG[CONF_COMPANY_ID]}"
    )
    flow._abort_if_unique_id_configured.assert_called_once()


async def test_already_configured_aborts():
    flow = _make_flow()
    flow._abort_if_unique_id_configured = MagicMock(
        side_effect=AbortFlow("already_configured")
    )
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={"data": {"name": "X"}})
        with pytest.raises(AbortFlow) as exc_info:
            await flow.async_step_user(MOCK_CONFIG)

    assert exc_info.value.reason == "already_configured"


async def test_title_falls_back_to_company_id_when_name_missing():
    flow = _make_flow()
    with patch(_SESSION_PATH), patch(_API_PATH) as MockAPI:
        MockAPI.return_value.get_user = AsyncMock(return_value={})
        result = await flow.async_step_user(MOCK_CONFIG)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert MOCK_CONFIG[CONF_COMPANY_ID] in result["title"]
