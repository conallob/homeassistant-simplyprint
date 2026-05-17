from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.simplyprint.api import SimplyPrintConnectionError
from custom_components.simplyprint.coordinator import SimplyPrintCoordinator
from tests.conftest import SAMPLE_PRINTER, SAMPLE_SPOOL


@pytest.fixture
def coordinator(hass, mock_api):
    return SimplyPrintCoordinator(hass, mock_api)


async def test_update_success(coordinator, mock_api):
    data = await coordinator._async_update_data()

    assert 1 in data["spools"]
    assert data["spools"][1] == SAMPLE_SPOOL
    assert 10 in data["printers"]
    assert data["printers"][10] == SAMPLE_PRINTER


async def test_update_indexes_by_id(coordinator, mock_api):
    mock_api.get_filament.return_value = [
        {**SAMPLE_SPOOL, "id": 1},
        {**SAMPLE_SPOOL, "id": 2, "name": "Blue PETG"},
    ]
    data = await coordinator._async_update_data()
    assert set(data["spools"].keys()) == {1, 2}


async def test_update_skips_spools_without_id(coordinator, mock_api):
    mock_api.get_filament.return_value = [{"name": "No ID spool"}, SAMPLE_SPOOL]
    data = await coordinator._async_update_data()
    assert list(data["spools"].keys()) == [1]


async def test_update_raises_update_failed_on_connection_error(coordinator, mock_api):
    mock_api.get_filament.side_effect = SimplyPrintConnectionError("timeout")
    with pytest.raises(UpdateFailed, match="SimplyPrint API error"):
        await coordinator._async_update_data()


async def test_update_raises_update_failed_on_printer_error(coordinator, mock_api):
    mock_api.get_printers.side_effect = SimplyPrintConnectionError("500")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_calls_both_endpoints_concurrently(coordinator, mock_api):
    """Both get_filament and get_printers should be called on each refresh."""
    await coordinator._async_update_data()
    mock_api.get_filament.assert_called_once()
    mock_api.get_printers.assert_called_once()
