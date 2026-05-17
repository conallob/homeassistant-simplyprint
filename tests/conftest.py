from unittest.mock import AsyncMock, MagicMock

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

MOCK_CONFIG = {
    "api_key": "test-api-key-123",
    "company_id": "42",
}

SAMPLE_SPOOL = {
    "id": 1,
    "uid": "ABCD",
    "name": "Red PLA",
    "brand": {"name": "Polymaker"},
    "material": "PLA",
    "color": {"hex": "#FF0000", "name": "Red"},
    "weight": 1000,
    "weight_used": 250,
    "printer_id": 10,
    "printer_name": "Ender 3",
    "location_name": "Shelf A",
    "dried_at": "2024-01-15T10:00:00Z",
}

SAMPLE_PRINTER = {
    "id": 10,
    "name": "Ender 3",
    "status": "printing",
    "job": {"name": "benchy.gcode", "progress": 45.2},
    "temps": {
        "tool0": {"actual": 210.0, "target": 210.0},
        "bed": {"actual": 60.0, "target": 60.0},
    },
}


@pytest.fixture
def mock_api():
    api = AsyncMock()
    api.get_user.return_value = {"data": {"name": "Test Company"}}
    api.get_filament.return_value = [SAMPLE_SPOOL]
    api.get_printers.return_value = [SAMPLE_PRINTER]
    api.assign_filament.return_value = {"status": True}
    api.unassign_filament.return_value = {"status": True}
    api.adjust_weight.return_value = {"status": True}
    api.mark_dried.return_value = {"status": True}
    return api


@pytest.fixture
def coordinator_data():
    return {
        "spools": {SAMPLE_SPOOL["id"]: SAMPLE_SPOOL},
        "printers": {SAMPLE_PRINTER["id"]: SAMPLE_PRINTER},
    }


@pytest.fixture
def mock_coordinator(coordinator_data):
    coord = MagicMock()
    coord.data = coordinator_data
    coord.async_request_refresh = AsyncMock()
    return coord


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = MOCK_CONFIG
    return entry
