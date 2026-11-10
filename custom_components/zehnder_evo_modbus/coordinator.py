"""Data update coordinator for the Zehnder EVO Connect ModBus bridge."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FILTER_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_WORD_ORDER,
    DEFAULT_FILTER_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WORD_ORDER,
    WordOrder,
)
from .modbus_client import ZehnderModbusClient, ZehnderModbusError
from .registers import (
    CAP_AFTERHEATER,
    CAP_PREHEATER,
    READ_BLOCKS,
    decode_all,
    encode_float,
)

_LOGGER = logging.getLogger(__name__)


class CapabilityInfo(TypedDict):
    """Device capability flags derived from register 41027."""

    known: bool
    preheater: bool
    afterheater: bool


UNKNOWN_CAPABILITIES: CapabilityInfo = {
    "known": False,
    "preheater": False,
    "afterheater": False,
}


class ZehnderEvoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the bridge and decode registers into a key -> value map."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZehnderModbusClient,
        entry_id: str,
        options: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="zehnder_evo_modbus",
            config_entry=self._entry_for_coordinator(hass, entry_id),
            update_interval=timedelta(
                seconds=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self._client = client
        self._entry_id = entry_id
        self._slave_id = options.get(CONF_SLAVE_ID, 1)
        self.word_order: WordOrder = options.get(CONF_WORD_ORDER, DEFAULT_WORD_ORDER)
        self._filter_interval = timedelta(
            seconds=options.get(CONF_FILTER_SCAN_INTERVAL, DEFAULT_FILTER_SCAN_INTERVAL)
        )
        self._raw: dict[int, int] = {}
        self._last_filter_poll: float | None = None
        self.capabilities: CapabilityInfo = dict(UNKNOWN_CAPABILITIES)
        self._write_lock = asyncio.Lock()

    @staticmethod
    def _entry_for_coordinator(hass: HomeAssistant, entry_id: str) -> Any:
        """Return the config entry so the coordinator is linked to it."""
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Read all register blocks and decode them."""
        raw = dict(self._raw)
        any_success = False
        now = time.monotonic()

        for block in READ_BLOCKS:
            if block.slow and (
                self._last_filter_poll is not None
                and (now - self._last_filter_poll)
                < self._filter_interval.total_seconds()
            ):
                continue
            try:
                registers = await self._client.async_read_holding(
                    block.address, block.count
                )
            except ZehnderModbusError as err:
                _LOGGER.warning("Error reading %s block: %s", block.name, err)
                continue
            for offset, value in enumerate(registers):
                raw[block.address + offset] = value
            any_success = True
            if block.slow:
                self._last_filter_poll = now

        if not any_success:
            raise UpdateFailed("No Modbus block could be read")

        self._raw = raw
        data = decode_all(raw, self.word_order)

        bits = data.get("fan_speed_bits")
        if isinstance(bits, int):
            self.capabilities = {
                "known": True,
                "preheater": bool(bits & CAP_PREHEATER),
                "afterheater": bool(bits & CAP_AFTERHEATER),
            }
        else:
            self.capabilities = dict(UNKNOWN_CAPABILITIES)
        data["capabilities"] = self.capabilities
        return data

    # -- writes --------------------------------------------------------------

    async def _async_write(self, write_call) -> None:
        """Run a write serialized, then refresh the polled data."""
        async with self._write_lock:
            await write_call()
        await self.async_request_refresh()

    async def async_write_required_speed(self, speed: int) -> None:
        """Write register 41500 (required ventilation speed)."""

        async def _call() -> None:
            await self._client.async_write_register(1499, int(speed))

        await self._async_write(_call)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single register."""

        async def _call() -> None:
            await self._client.async_write_register(address, int(value))

        await self._async_write(_call)

    async def async_write_float(self, address: int, value: float) -> None:
        """Write a 2-register float value."""

        async def _call() -> None:
            words = encode_float(value, self.word_order)
            try:
                await self._client.async_write_registers(address, words)
            except ZehnderModbusError as err:
                # Some bridges reject FC16 for 32-bit float registers but
                # accept the two words written individually (FC06).
                _LOGGER.debug(
                    "FC16 write to %s failed (%s), falling back to FC06", address, err
                )
                await self._client.async_write_register(address, words[0])
                await self._client.async_write_register(address + 1, words[1])

        await self._async_write(_call)

    async def async_reset_filter_timer(self) -> None:
        """Reset the air filter timer (write 0 to 42000)."""

        async def _call() -> None:
            await self._client.async_write_register(1999, 0)

        await self._async_write(_call)
