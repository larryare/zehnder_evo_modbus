"""Tests that set up the integration end to end with a fake bridge."""

from typing import ClassVar
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zehnder_evo_modbus.const import DOMAIN
from tests.memory import SERIAL_CONFIG, build_memory


class FakeSetupClient:
    """Fake ZehnderModbusClient serving a fixed memory map."""

    instances: ClassVar[list] = []

    def __init__(self, config):
        self.config = config
        self.memory = build_memory()
        self.connected = True
        FakeSetupClient.instances.append(self)

    async def async_connect(self):
        return True

    async def async_close(self):
        return None

    async def async_read_holding(self, address, count):
        return [self.memory.get(address + i, 0) for i in range(count)]

    async def async_write_register(self, address, value):
        self.memory[address] = value

    async def async_write_registers(self, address, values):
        for i, value in enumerate(values):
            self.memory[address + i] = value


def _patch_client():
    return patch(
        "custom_components.zehnder_evo_modbus.ZehnderModbusClient",
        FakeSetupClient,
    )


async def _setup(hass):
    FakeSetupClient.instances = []
    entry = MockConfigEntry(domain=DOMAIN, data=dict(SERIAL_CONFIG))
    entry.add_to_hass(hass)
    with _patch_client():
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_setup_creates_device_and_entities(hass, enable_custom_integrations):
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    # device exists
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Zehnder"

    entity_registry = er.async_get(hass)
    entries = [
        entity_entry
        for entity_entry in entity_registry.entities.values()
        if entity_entry.config_entry_id == entry.entry_id
    ]
    keys = {entity_entry.unique_id.split("_", 1)[1] for entity_entry in entries}
    assert "supply_temp" in keys
    assert "ventilation" in keys
    assert "filter_timer_reset" in keys
    assert "standby_supply_pct" in keys


async def test_fan_state_and_preset(hass, enable_custom_integrations):
    await _setup(hass)

    state = hass.states.get("fan.zehnder_evo")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["preset_mode"] == "medium"
    assert state.attributes["percentage"] == 50


async def test_sensor_values(hass, enable_custom_integrations):
    await _setup(hass)

    supply = hass.states.get("sensor.zehnder_evo_supply_air_temperature")
    assert supply is not None
    assert float(supply.state) == 18.5

    airflow = hass.states.get("sensor.zehnder_evo_supply_airflow")
    assert airflow is not None
    assert float(airflow.state) == 120.0
    assert airflow.attributes["unit_of_measurement"] == "m³/h"

    humidity = hass.states.get("sensor.zehnder_evo_outdoor_humidity")
    # 0xEF sentinel -> unknown
    assert humidity.state == "unknown"

    co2 = hass.states.get("sensor.zehnder_evo_co2_level")
    assert float(co2.state) == 650.0


async def test_binary_sensors(hass, enable_custom_integrations):
    await _setup(hass)

    dirty = hass.states.get("binary_sensor.zehnder_evo_dirty_filter")
    assert dirty is not None
    assert dirty.state == "off"

    rf = hass.states.get("binary_sensor.zehnder_evo_rf_communication_lost")
    assert rf is not None
    assert rf.state == "off"


async def test_number_values_and_write(hass, enable_custom_integrations):
    await _setup(hass)

    number = hass.states.get("number.zehnder_evo_speed_2_supply_airflow")
    assert number is not None
    assert float(number.state) == 70.0

    client = FakeSetupClient.instances[-1]

    entity_components = hass.data["entity_components"]
    number_platform = entity_components.get("number")
    entity = next(
        e for e in number_platform.entities if e.unique_id.endswith("speed2_supply_pct")
    )
    await entity.async_set_native_value(80)
    await hass.async_block_till_done()
    assert client.memory[2004] == 80


async def test_fan_preset_write(hass, enable_custom_integrations):
    await _setup(hass)
    client = FakeSetupClient.instances[-1]

    fan = next(iter(hass.data["entity_components"].get("fan").entities))
    await fan.async_set_preset_mode("boost")
    await hass.async_block_till_done()
    assert client.memory[1499] == 7


async def test_filter_reset_button(hass, enable_custom_integrations):
    await _setup(hass)
    client = FakeSetupClient.instances[-1]

    button = next(iter(hass.data["entity_components"].get("button").entities))
    await button.async_press()
    await hass.async_block_till_done()
    assert client.memory[1999] == 0


async def test_unload(hass, enable_custom_integrations):
    entry = await _setup(hass)
    with _patch_client():
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
