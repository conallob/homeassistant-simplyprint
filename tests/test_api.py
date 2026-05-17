from __future__ import annotations

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.simplyprint.api import (
    SimplyPrintAPI,
    SimplyPrintAuthError,
    SimplyPrintConnectionError,
)

BASE = "https://api.simplyprint.io/42"


@pytest.fixture
async def api():
    session = aiohttp.ClientSession()
    yield SimplyPrintAPI("test-key", "42", session)
    await session.close()


class TestGetUser:
    async def test_success(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/account/GetUser", payload={"data": {"name": "Acme"}})
            result = await api.get_user()
        assert result["data"]["name"] == "Acme"

    async def test_sends_auth_header(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/account/GetUser", payload={})
            await api.get_user()
            request = list(m.requests.values())[0][0]
        assert request.kwargs["headers"]["X-API-Key"] == "test-key"

    async def test_401_raises_auth_error(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/account/GetUser", status=401)
            with pytest.raises(SimplyPrintAuthError):
                await api.get_user()

    async def test_500_raises_connection_error(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/account/GetUser", status=500)
            with pytest.raises(SimplyPrintConnectionError):
                await api.get_user()

    async def test_timeout_raises_connection_error(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/account/GetUser", exception=asyncio.TimeoutError())
            with pytest.raises(SimplyPrintConnectionError):
                await api.get_user()


class TestGetFilament:
    async def test_returns_data_key(self, api):
        spools = [{"id": 1, "name": "PLA Red"}]
        with aioresponses() as m:
            m.post(f"{BASE}/filament/GetFilament", payload={"data": spools})
            result = await api.get_filament()
        assert result == spools

    async def test_returns_filament_key_fallback(self, api):
        spools = [{"id": 2, "name": "PETG Blue"}]
        with aioresponses() as m:
            m.post(f"{BASE}/filament/GetFilament", payload={"filament": spools})
            result = await api.get_filament()
        assert result == spools

    async def test_returns_spools_key_fallback(self, api):
        spools = [{"id": 3, "name": "ABS Black"}]
        with aioresponses() as m:
            m.post(f"{BASE}/filament/GetFilament", payload={"spools": spools})
            result = await api.get_filament()
        assert result == spools

    async def test_returns_empty_on_unknown_structure(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/filament/GetFilament", payload={"something_else": {}})
            result = await api.get_filament()
        assert result == []


class TestGetPrinters:
    async def test_returns_data_key(self, api):
        printers = [{"id": 10, "name": "Ender 3"}]
        with aioresponses() as m:
            m.post(f"{BASE}/printers/Get", payload={"data": printers})
            result = await api.get_printers()
        assert result == printers

    async def test_returns_printers_key_fallback(self, api):
        printers = [{"id": 11, "name": "Prusa MK4"}]
        with aioresponses() as m:
            m.post(f"{BASE}/printers/Get", payload={"printers": printers})
            result = await api.get_printers()
        assert result == printers


class TestMutatingEndpoints:
    async def test_assign_filament(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/filament/Assign", payload={"status": True})
            result = await api.assign_filament(filament_id=1, printer_id=10, extruder=0)
        assert result["status"] is True
        request = list(m.requests.values())[0][0]
        body = request.kwargs["json"]
        assert "1" in body["filament"]
        assert body["printer_id"] == 10

    async def test_unassign_filament(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/filament/Unassign", payload={"status": True})
            await api.unassign_filament(printer_id=10)
        request = list(m.requests.values())[0][0]
        assert request.kwargs["json"]["printer_id"] == 10

    async def test_adjust_weight(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/filament/AdjustWeight", payload={"status": True})
            await api.adjust_weight(filament_id=1, weight=500.0)
        request = list(m.requests.values())[0][0]
        body = request.kwargs["json"]
        assert body["id"] == 1
        assert body["weight"] == 500.0

    async def test_mark_dried(self, api):
        with aioresponses() as m:
            m.post(f"{BASE}/filament/MarkDried", payload={"status": True})
            await api.mark_dried(filament_id=1)
        request = list(m.requests.values())[0][0]
        assert request.kwargs["json"]["id"] == 1
