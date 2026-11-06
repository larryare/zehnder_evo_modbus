"""Tests for the coordinator using a fake Modbus client."""

from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.zehnder_evo_modbus.const import WordOrder
from custom_components.zehnder_evo_modbus.coordinator import ZehnderEvoCoordinator
from custom_components.zehnder_evo_modbus.modbus_client import ZehnderModbusError
from tests.memory import build_memory


class FakeMemoryClient:
    """Serves a fixed register memory map."""

    def __init__(self, memory=None):
        self.memory = memory or {}
        self.read_calls = []

    async def async_connect(self):
        return True

    async def async_close(self):
        return None

    async def async_read_holding(self, address, count):
        self.read_calls.append((address, count))
        return [self.memory.get(address + i, 0) for i in range(count)]

    async def async_write_register(self, address, value):
        self.memory[address] = value

    async def async_write_registers(self, address, values):
        for i, value in enumerate(values):
            self.memory[address + i] = value


def _make_coordinator(client, options=None):
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = None
    coordinator = ZehnderEvoCoordinator(
        hass, client, "test_entry", options or {}
    )
    # bypass the config entry lookup dependency
    coordinator._entry_id = "test_entry"
    return coordinator


async def test_update_decodes_all_blocks():
    client = FakeMemoryClient(build_memory())
    coordinator = _make_coordinator(client)

    data = await coordinator._async_update_data()

    assert data["required_speed"] == 3
    assert data["current_fan_speed"] == 2
    assert data["extraction_temp"] == 20.0
    assert data["outdoor_temp"] == 5.0
    assert data["supply_flow"] == 120.0
    assert data["indoor_humidity"] == 45
    assert data["outdoor_humidity"] is None
    assert data["afterheater_pct"] is None
    assert data["co2"] == 650
    assert data["filter_days_remaining"] == 40
    assert coordinator.capabilities == {
        "known": True,
        "preheater": True,
        "afterheater": True,
    }


async def test_update_raises_when_all_blocks_fail():
    class FailingClient(FakeMemoryClient):
        async def async_read_holding(self, address, count):
            raise ZehnderModbusError("boom")

    coordinator = _make_coordinator(FailingClient())
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_partial_failure_keeps_previous_values():
    client = FakeMemoryClient(build_memory())
    coordinator = _make_coordinator(client)
    await coordinator._async_update_data()

    # now the sensors block starts failing, other blocks keep working
    original_read = client.async_read_holding

    async def flaky(address, count):
        if address == 999:
            raise ZehnderModbusError("boom")
        return await original_read(address, count)

    client.async_read_holding = flaky
    data = await coordinator._async_update_data()
    # previous decoded sensor value is retained (stale but present)
    assert data["current_fan_speed"] == 2
    # required speed block still read
    assert data["required_speed"] == 3


async def test_filter_block_is_polled_slowly():
    client = FakeMemoryClient(build_memory())
    coordinator = _make_coordinator(
        client, {"filter_scan_interval": 3600}
    )
    await coordinator._async_update_data()
    filter_reads = [c for c in client.read_calls if c[0] == 1039]
    assert len(filter_reads) == 1  # first update reads the filter block

    # immediate second update must skip the slow block
    await coordinator._async_update_data()
    filter_reads = [c for c in client.read_calls if c[0] == 1039]
    assert len(filter_reads) == 1


async def test_write_required_speed_updates_memory():
    client = FakeMemoryClient(build_memory())
    coordinator = _make_coordinator(client)
    await coordinator._async_update_data()

    async def fake_refresh():
        return None

    coordinator.async_request_refresh = fake_refresh
    await coordinator.async_write_required_speed(7)
    assert client.memory[1499] == 7


async def test_write_float_uses_word_order():
    client = FakeMemoryClient(build_memory())
    coordinator = _make_coordinator(client)

    async def fake_refresh():
        return None

    coordinator.async_request_refresh = fake_refresh
    coordinator.word_order = WordOrder.LITTLE
    await coordinator.async_write_float(2010, 5.0)
    # 5.0 = 0x40A00000 -> little word order writes [0x0000, 0x40A0]
    assert client.memory[2010] == 0x0000
    assert client.memory[2011] == 0x40A0
