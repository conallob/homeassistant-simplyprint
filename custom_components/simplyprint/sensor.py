from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SimplyPrintCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SimplyPrintCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for spool_id in coordinator.data["spools"]:
        entities.append(SimplyPrintSpoolSensor(coordinator, entry, spool_id))
    for printer_id in coordinator.data["printers"]:
        entities.append(SimplyPrintPrinterSensor(coordinator, entry, printer_id))

    async_add_entities(entities)

    # Track new spools/printers added between HA restarts
    def _handle_coordinator_update() -> None:
        existing_ids = {e.unique_id for e in entities}
        new_entities: list[SensorEntity] = []

        for spool_id in coordinator.data["spools"]:
            uid = f"{entry.entry_id}_spool_{spool_id}"
            if uid not in existing_ids:
                sensor = SimplyPrintSpoolSensor(coordinator, entry, spool_id)
                entities.append(sensor)
                new_entities.append(sensor)

        for printer_id in coordinator.data["printers"]:
            uid = f"{entry.entry_id}_printer_{printer_id}"
            if uid not in existing_ids:
                sensor = SimplyPrintPrinterSensor(coordinator, entry, printer_id)
                entities.append(sensor)
                new_entities.append(sensor)

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))


def _color_hex(spool: dict[str, Any]) -> str | None:
    color = spool.get("color")
    if isinstance(color, dict):
        return color.get("hex") or color.get("hexColor")
    return None


def _color_name(spool: dict[str, Any]) -> str | None:
    color = spool.get("color")
    if isinstance(color, dict):
        return color.get("name")
    return spool.get("color_name")


def _brand_name(spool: dict[str, Any]) -> str | None:
    brand = spool.get("brand")
    if isinstance(brand, dict):
        return brand.get("name")
    return brand


def _material_name(spool: dict[str, Any]) -> str | None:
    material = spool.get("material")
    if isinstance(material, dict):
        return material.get("name") or material.get("type")
    return material or spool.get("type")


def _weight_remaining(spool: dict[str, Any]) -> float | None:
    # Try direct field first, then calculate from total - used
    if "weight_remaining" in spool:
        return float(spool["weight_remaining"])
    total = spool.get("weight") or spool.get("weight_total")
    used = spool.get("weight_used") or spool.get("used_weight", 0)
    if total is not None:
        return max(0.0, float(total) - float(used))
    return None


class SimplyPrintSpoolSensor(CoordinatorEntity[SimplyPrintCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_name = "Weight Remaining"

    def __init__(
        self,
        coordinator: SimplyPrintCoordinator,
        entry: ConfigEntry,
        spool_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._spool_id = spool_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_spool_{spool_id}"

    @property
    def _spool(self) -> dict[str, Any]:
        return self.coordinator.data["spools"].get(self._spool_id, {})

    @property
    def available(self) -> bool:
        return self._spool_id in self.coordinator.data["spools"]

    @property
    def native_value(self) -> float | None:
        return _weight_remaining(self._spool)

    @property
    def device_info(self) -> DeviceInfo:
        spool = self._spool
        name = spool.get("name") or f"Spool {self._spool_id}"
        brand = _brand_name(spool)
        model = _material_name(spool) or "Filament Spool"
        return DeviceInfo(
            identifiers={(DOMAIN, f"spool_{self._spool_id}")},
            name=name,
            manufacturer=brand,
            model=model,
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        spool = self._spool
        attrs: dict[str, Any] = {
            "spool_id": self._spool_id,
            "uid": spool.get("uid"),
            "brand": _brand_name(spool),
            "material": _material_name(spool),
            "color_name": _color_name(spool),
            "color_hex": _color_hex(spool),
            "weight_total_g": spool.get("weight") or spool.get("weight_total"),
            "weight_used_g": spool.get("weight_used") or spool.get("used_weight"),
            "location": spool.get("location_name") or spool.get("location"),
            "assigned_printer_id": spool.get("printer_id"),
            "assigned_printer_name": spool.get("printer_name"),
            "last_dried_at": spool.get("dried_at") or spool.get("last_dried_at"),
            "nfc_id": spool.get("nfc_id") or spool.get("uid"),
        }
        return {k: v for k, v in attrs.items() if v is not None}


class SimplyPrintPrinterSensor(CoordinatorEntity[SimplyPrintCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:printer-3d"

    def __init__(
        self,
        coordinator: SimplyPrintCoordinator,
        entry: ConfigEntry,
        printer_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._printer_id = printer_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_printer_{printer_id}"

    @property
    def _printer(self) -> dict[str, Any]:
        return self.coordinator.data["printers"].get(self._printer_id, {})

    @property
    def available(self) -> bool:
        return self._printer_id in self.coordinator.data["printers"]

    @property
    def native_value(self) -> str:
        printer = self._printer
        # Status may be a string or integer code
        status = printer.get("status") or printer.get("state")
        if isinstance(status, int):
            return _printer_status_name(status)
        return str(status) if status else "unknown"

    @property
    def device_info(self) -> DeviceInfo:
        printer = self._printer
        name = printer.get("name") or f"Printer {self._printer_id}"
        return DeviceInfo(
            identifiers={(DOMAIN, f"printer_{self._printer_id}")},
            name=name,
            model=printer.get("model") or printer.get("type"),
            manufacturer=printer.get("brand"),
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        printer = self._printer
        job = printer.get("job") or printer.get("current_job") or {}
        temps = printer.get("temps") or printer.get("temperatures") or {}

        tool = temps.get("tool0") or temps.get("nozzle") or {}
        bed = temps.get("bed") or {}

        attrs: dict[str, Any] = {
            "printer_id": self._printer_id,
            "current_job": job.get("name") or job.get("filename"),
            "job_progress": job.get("progress"),
            "nozzle_temp_actual": tool.get("actual"),
            "nozzle_temp_target": tool.get("target"),
            "bed_temp_actual": bed.get("actual"),
            "bed_temp_target": bed.get("target"),
            "assigned_spool_id": printer.get("filament_id") or printer.get("spool_id"),
        }
        return {k: v for k, v in attrs.items() if v is not None}


def _printer_status_name(code: int) -> str:
    _STATUS_MAP = {
        0: "offline",
        1: "idle",
        2: "printing",
        3: "paused",
        4: "pausing",
        5: "cancelling",
        6: "error",
        7: "heating",
        8: "operational",
    }
    return _STATUS_MAP.get(code, f"unknown_{code}")
