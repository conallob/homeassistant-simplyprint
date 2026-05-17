from __future__ import annotations

import pytest

from custom_components.simplyprint.sensor import (
    SimplyPrintPrinterSensor,
    SimplyPrintSpoolSensor,
    _brand_name,
    _color_hex,
    _color_name,
    _material_name,
    _printer_status_name,
    _weight_remaining,
)


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------


class TestColorHex:
    def test_from_hex_key(self):
        assert _color_hex({"color": {"hex": "#FF0000"}}) == "#FF0000"

    def test_from_hexColor_key(self):
        assert _color_hex({"color": {"hexColor": "#00FF00"}}) == "#00FF00"

    def test_hex_takes_priority_over_hexColor(self):
        assert _color_hex({"color": {"hex": "#111", "hexColor": "#222"}}) == "#111"

    def test_missing_color_key(self):
        assert _color_hex({}) is None

    def test_color_not_a_dict(self):
        assert _color_hex({"color": "red"}) is None


class TestColorName:
    def test_from_color_dict(self):
        assert _color_name({"color": {"name": "Red"}}) == "Red"

    def test_fallback_to_color_name_field(self):
        assert _color_name({"color_name": "Blue"}) == "Blue"

    def test_missing(self):
        assert _color_name({}) is None


class TestBrandName:
    def test_from_dict(self):
        assert _brand_name({"brand": {"name": "Polymaker"}}) == "Polymaker"

    def test_from_string(self):
        assert _brand_name({"brand": "Bambu"}) == "Bambu"

    def test_missing(self):
        assert _brand_name({}) is None


class TestMaterialName:
    def test_from_string(self):
        assert _material_name({"material": "PLA"}) == "PLA"

    def test_from_dict_name(self):
        assert _material_name({"material": {"name": "PETG"}}) == "PETG"

    def test_from_dict_type(self):
        assert _material_name({"material": {"type": "ABS"}}) == "ABS"

    def test_fallback_to_type_field(self):
        assert _material_name({"type": "TPU"}) == "TPU"

    def test_missing(self):
        assert _material_name({}) is None


class TestWeightRemaining:
    def test_direct_field(self):
        assert _weight_remaining({"weight_remaining": 750}) == 750.0

    def test_calculated_from_total_and_used(self):
        assert _weight_remaining({"weight": 1000, "weight_used": 250}) == 750.0

    def test_uses_weight_total_alias(self):
        assert _weight_remaining({"weight_total": 1000, "weight_used": 100}) == 900.0

    def test_uses_used_weight_alias(self):
        assert _weight_remaining({"weight": 1000, "used_weight": 400}) == 600.0

    def test_clamps_to_zero_when_overused(self):
        assert _weight_remaining({"weight": 100, "weight_used": 200}) == 0.0

    def test_no_data_returns_none(self):
        assert _weight_remaining({}) is None

    def test_direct_field_takes_priority(self):
        # weight_remaining should be used even if total/used are also present
        result = _weight_remaining({"weight_remaining": 500, "weight": 1000, "weight_used": 100})
        assert result == 500.0


class TestPrinterStatusName:
    @pytest.mark.parametrize(
        "code,expected",
        [
            (0, "offline"),
            (1, "idle"),
            (2, "printing"),
            (3, "paused"),
            (4, "pausing"),
            (5, "cancelling"),
            (6, "error"),
            (7, "heating"),
            (8, "operational"),
        ],
    )
    def test_known_codes(self, code, expected):
        assert _printer_status_name(code) == expected

    def test_unknown_code(self):
        assert _printer_status_name(99) == "unknown_99"


# ---------------------------------------------------------------------------
# Spool sensor entity tests
# ---------------------------------------------------------------------------


class TestSimplyPrintSpoolSensor:
    def setup_method(self):
        from unittest.mock import MagicMock

        from tests.conftest import SAMPLE_SPOOL

        coord = MagicMock()
        coord.data = {"spools": {1: SAMPLE_SPOOL}, "printers": {}}
        entry = MagicMock()
        entry.entry_id = "entry_abc"
        self.sensor = SimplyPrintSpoolSensor(coord, entry, 1)

    def test_unique_id(self):
        assert self.sensor.unique_id == "entry_abc_spool_1"

    def test_native_value_calculated(self):
        assert self.sensor.native_value == 750.0

    def test_available_true(self):
        assert self.sensor.available is True

    def test_available_false_for_missing_spool(self):
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.data = {"spools": {}, "printers": {}}
        entry = MagicMock()
        entry.entry_id = "e"
        sensor = SimplyPrintSpoolSensor(coord, entry, 999)
        assert sensor.available is False

    def test_extra_attributes_material(self):
        assert self.sensor.extra_state_attributes["material"] == "PLA"

    def test_extra_attributes_color_hex(self):
        assert self.sensor.extra_state_attributes["color_hex"] == "#FF0000"

    def test_extra_attributes_color_name(self):
        assert self.sensor.extra_state_attributes["color_name"] == "Red"

    def test_extra_attributes_brand(self):
        assert self.sensor.extra_state_attributes["brand"] == "Polymaker"

    def test_extra_attributes_location(self):
        assert self.sensor.extra_state_attributes["location"] == "Shelf A"

    def test_extra_attributes_assigned_printer(self):
        assert self.sensor.extra_state_attributes["assigned_printer_id"] == 10

    def test_extra_attributes_last_dried(self):
        assert self.sensor.extra_state_attributes["last_dried_at"] == "2024-01-15T10:00:00Z"

    def test_extra_attributes_no_none_values(self):
        attrs = self.sensor.extra_state_attributes
        assert all(v is not None for v in attrs.values())

    def test_device_info_has_correct_identifier(self):
        info = self.sensor.device_info
        assert (("simplyprint", "spool_1")) in info["identifiers"]

    def test_device_info_manufacturer(self):
        assert self.sensor.device_info["manufacturer"] == "Polymaker"


class TestSimplyPrintSpoolSensorWeightVariants:
    """Test that weight_remaining is computed correctly for various API shapes."""

    def _make_sensor(self, spool_data):
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.data = {"spools": {1: {**spool_data, "id": 1}}, "printers": {}}
        entry = MagicMock()
        entry.entry_id = "e"
        return SimplyPrintSpoolSensor(coord, entry, 1)

    def test_weight_remaining_direct(self):
        sensor = self._make_sensor({"weight_remaining": 300})
        assert sensor.native_value == 300.0

    def test_weight_remaining_via_total_and_used(self):
        sensor = self._make_sensor({"weight": 800, "weight_used": 200})
        assert sensor.native_value == 600.0

    def test_weight_remaining_none_when_no_data(self):
        sensor = self._make_sensor({})
        assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Printer sensor entity tests
# ---------------------------------------------------------------------------


class TestSimplyPrintPrinterSensor:
    def setup_method(self):
        from unittest.mock import MagicMock

        from tests.conftest import SAMPLE_PRINTER

        coord = MagicMock()
        coord.data = {"spools": {}, "printers": {10: SAMPLE_PRINTER}}
        entry = MagicMock()
        entry.entry_id = "entry_abc"
        self.sensor = SimplyPrintPrinterSensor(coord, entry, 10)

    def test_unique_id(self):
        assert self.sensor.unique_id == "entry_abc_printer_10"

    def test_native_value_string_status(self):
        assert self.sensor.native_value == "printing"

    def test_native_value_integer_status(self):
        from unittest.mock import MagicMock

        from tests.conftest import SAMPLE_PRINTER

        coord = MagicMock()
        coord.data = {"spools": {}, "printers": {10: {**SAMPLE_PRINTER, "status": 2}}}
        entry = MagicMock()
        entry.entry_id = "e"
        sensor = SimplyPrintPrinterSensor(coord, entry, 10)
        assert sensor.native_value == "printing"

    def test_native_value_unknown_falls_back(self):
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.data = {"spools": {}, "printers": {10: {"id": 10, "name": "X"}}}
        entry = MagicMock()
        entry.entry_id = "e"
        sensor = SimplyPrintPrinterSensor(coord, entry, 10)
        assert sensor.native_value == "unknown"

    def test_available_true(self):
        assert self.sensor.available is True

    def test_available_false_for_missing_printer(self):
        from unittest.mock import MagicMock

        coord = MagicMock()
        coord.data = {"spools": {}, "printers": {}}
        entry = MagicMock()
        entry.entry_id = "e"
        sensor = SimplyPrintPrinterSensor(coord, entry, 999)
        assert sensor.available is False

    def test_extra_attributes_current_job(self):
        assert self.sensor.extra_state_attributes["current_job"] == "benchy.gcode"

    def test_extra_attributes_progress(self):
        assert self.sensor.extra_state_attributes["job_progress"] == 45.2

    def test_extra_attributes_nozzle_temp(self):
        assert self.sensor.extra_state_attributes["nozzle_temp_actual"] == 210.0

    def test_extra_attributes_bed_temp(self):
        assert self.sensor.extra_state_attributes["bed_temp_actual"] == 60.0

    def test_extra_attributes_no_none_values(self):
        attrs = self.sensor.extra_state_attributes
        assert all(v is not None for v in attrs.values())

    def test_device_info_identifier(self):
        info = self.sensor.device_info
        assert ("simplyprint", "printer_10") in info["identifiers"]
