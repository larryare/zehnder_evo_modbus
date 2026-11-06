"""Async Modbus client wrapper for the Zehnder EVO Connect ModBus bridge."""

from __future__ import annotations

import asyncio
import logging
from inspect import signature
from typing import Any

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_FRAMING,
    CONF_HOST,
    CONF_PARITY,
    CONF_SERIAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONF_STOPBITS,
    CONF_TCP_PORT,
    DEFAULT_TCP_PORT,
    Framing,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0

try:
    from pymodbus import FramerType

    _FRAMERS: dict[str, Any] = {
        Framing.RTU: FramerType.RTU,
        Framing.TCP: FramerType.SOCKET,
    }
except ImportError:  # pragma: no cover - pymodbus < 3.8
    from pymodbus.framer import ModbusRtuFramer, ModbusSocketFramer

    _FRAMERS = {
        Framing.RTU: ModbusRtuFramer,
        Framing.TCP: ModbusSocketFramer,
    }


class ZehnderModbusError(Exception):
    """Error communicating with the EVO Connect ModBus bridge."""


class ZehnderModbusClient:
    """Thin wrapper around pymodbus providing a stable, version-tolerant API."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Build the wrapper from merged entry data/options."""
        self._config = config
        self._client: Any = None
        self._id_kwarg = "slave"
        self._lock = asyncio.Lock()

    # -- construction --------------------------------------------------------

    def _build_client(self) -> Any:
        connection = self._config[CONF_CONNECTION_TYPE]
        if connection == CONF_SERIAL:
            kwargs: dict[str, Any] = {
                "port": self._config[CONF_SERIAL_PORT],
                "baudrate": self._config.get(CONF_BAUDRATE, 9600),
                "parity": self._config.get(CONF_PARITY, "N"),
                "stopbits": self._config.get(CONF_STOPBITS, 1),
                "bytesize": self._config.get(CONF_BYTESIZE, 8),
                "timeout": REQUEST_TIMEOUT,
            }
            try:
                return AsyncModbusSerialClient(**kwargs)
            except TypeError:  # pragma: no cover - pymodbus < 3.7 requires method=
                kwargs["method"] = "rtu"
                return AsyncModbusSerialClient(**kwargs)

        kwargs = {
            "host": self._config[CONF_HOST],
            "port": self._config.get(CONF_TCP_PORT, DEFAULT_TCP_PORT),
            "timeout": REQUEST_TIMEOUT,
        }
        framer = _FRAMERS.get(self._config.get(CONF_FRAMING, Framing.RTU))
        if framer is not None:
            kwargs["framer"] = framer
        return AsyncModbusTcpClient(**kwargs)

    @property
    def _pymodbus_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    # -- connection ----------------------------------------------------------

    async def async_connect(self) -> bool:
        """Connect to the bridge. Returns True on success."""
        client = self._pymodbus_client
        try:
            async with self._lock:
                connected = await client.connect()
        except (TimeoutError, ModbusException, OSError) as err:
            _LOGGER.debug("Connection failed: %s", err)
            return False
        if not connected:
            return False
        params = signature(client.read_holding_registers).parameters
        # pymodbus >= 3.9 renamed the slave keyword to device_id.
        self._id_kwarg = "device_id" if "device_id" in params else "slave"
        return True

    async def async_close(self) -> None:
        """Close the underlying connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                _LOGGER.exception("Error while closing Modbus client")
            self._client = None

    # -- IO ------------------------------------------------------------------

    def _id_kwargs(self) -> dict[str, int]:
        return {self._id_kwarg: self._config[CONF_SLAVE_ID]}

    async def async_read_holding(self, address: int, count: int) -> list[int]:
        """Read holding registers (FC03). Raises ZehnderModbusError on failure."""
        client = self._pymodbus_client
        try:
            if not client.connected and not await self.async_connect():
                raise ZehnderModbusError("Not connected")
            result = await client.read_holding_registers(
                address, count=count, **self._id_kwargs()
            )
        except ModbusException as err:
            raise ZehnderModbusError(str(err)) from err
        except (TimeoutError, OSError) as err:
            raise ZehnderModbusError(str(err)) from err
        if result.isError():
            raise ZehnderModbusError(str(result))
        return list(result.registers)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single holding register (FC06)."""
        client = self._pymodbus_client
        try:
            if not client.connected and not await self.async_connect():
                raise ZehnderModbusError("Not connected")
            result = await client.write_register(address, value, **self._id_kwargs())
        except ModbusException as err:
            raise ZehnderModbusError(str(err)) from err
        except (TimeoutError, OSError) as err:
            raise ZehnderModbusError(str(err)) from err
        if result.isError():
            raise ZehnderModbusError(str(result))

    async def async_write_registers(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers (FC16)."""
        client = self._pymodbus_client
        try:
            if not client.connected and not await self.async_connect():
                raise ZehnderModbusError("Not connected")
            result = await client.write_registers(
                address, values, **self._id_kwargs()
            )
        except ModbusException as err:
            raise ZehnderModbusError(str(err)) from err
        except (TimeoutError, OSError) as err:
            raise ZehnderModbusError(str(err)) from err
        if result.isError():
            raise ZehnderModbusError(str(result))
