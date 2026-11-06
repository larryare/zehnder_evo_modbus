"""The Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DEFAULTS_BY_KEY
from .coordinator import ZehnderEvoCoordinator
from .modbus_client import ZehnderModbusClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Zehnder EVO Connect ModBus bridge from a config entry."""
    config = {**DEFAULTS_BY_KEY, **entry.data, **entry.options}

    client = ZehnderModbusClient(config)
    if not await client.async_connect():
        await client.async_close()
        raise ConfigEntryNotReady("Could not connect to the EVO Connect ModBus bridge")

    coordinator = ZehnderEvoCoordinator(hass, client, entry.entry_id, config)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ZehnderEvoCoordinator = entry.runtime_data
        await coordinator._client.async_close()
    return unload_ok
