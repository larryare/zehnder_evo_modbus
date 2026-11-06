"""Config flow for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_FILTER_SCAN_INTERVAL,
    CONF_FRAMING,
    CONF_HOST,
    CONF_PARITY,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONF_STOPBITS,
    CONF_TCP,
    CONF_TCP_PORT,
    CONF_WORD_ORDER,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FILTER_SCAN_INTERVAL,
    DEFAULT_PARITY,
    DEFAULT_SLAVE_ID,
    DEFAULT_STOPBITS,
    DEFAULT_TCP_PORT,
    DEFAULT_WORD_ORDER,
    DEVICE_NAME,
    Framing,
    WordOrder,
)
from .modbus_client import ZehnderModbusClient, ZehnderModbusError
from .registers import REGISTER_MAP

_LOGGER = logging.getLogger(__name__)

REQUIRED_SPEED_ADDRESS = REGISTER_MAP["required_speed"].address

CONNECTION_LABELS = {
    CONF_SERIAL: "Serial (USB RS485 adapter)",
    CONF_TCP: "Network (WiFi / Ethernet RS485 gateway)",
}


class CannotConnect(HomeAssistantError):
    """Error indicating the connection could not be established."""


async def _validate_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Check that the bridge answers on the given connection settings."""
    client = ZehnderModbusClient(data)
    try:
        if not await client.async_connect():
            raise CannotConnect
        await client.async_read_holding(REQUIRED_SPEED_ADDRESS, 1)
    except (ZehnderModbusError, CannotConnect) as err:
        raise CannotConnect from err
    finally:
        await client.async_close()


def _unique_id(data: dict[str, Any]) -> str:
    if data[CONF_CONNECTION_TYPE] == CONF_SERIAL:
        return f"{CONF_SERIAL}:{data[CONF_SERIAL_PORT]}:{data[CONF_SLAVE_ID]}"
    return (
        f"{CONF_TCP}:{data[CONF_HOST]}:{data[CONF_TCP_PORT]}:{data[CONF_SLAVE_ID]}"
    )


class ZehnderConfigFlow(config_entries.ConfigFlow, domain="zehnder_evo_modbus"):
    """Handle the config flow for Zehnder EVO Connect ModBus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: choose the connection type."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == CONF_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_tcp()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONNECTION_TYPE, default=CONF_SERIAL
                ): vol.In(CONNECTION_LABELS)
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2a: serial (USB RS485) connection settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: CONF_SERIAL, **user_input}
            try:
                await _validate_connection(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(_unique_id(data))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{DEVICE_NAME} ({data[CONF_SERIAL_PORT]})", data=data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT): str,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
                vol.Required(CONF_PARITY, default=DEFAULT_PARITY): vol.In(
                    ["N", "E", "O"]
                ),
                vol.Required(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.All(
                    cv.positive_int, vol.In([1, 2])
                ),
                vol.Required(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.All(
                    cv.positive_int, vol.In([7, 8])
                ),
                vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): cv.positive_int,
            }
        )
        return self.async_show_form(step_id="serial", data_schema=schema, errors=errors)

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2b: network (RTU over TCP) connection settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: CONF_TCP, **user_input}
            try:
                await _validate_connection(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(_unique_id(data))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{DEVICE_NAME} ({data[CONF_HOST]})", data=data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_TCP_PORT, default=DEFAULT_TCP_PORT): cv.port,
                vol.Required(CONF_FRAMING, default=Framing.RTU): vol.In(
                    {
                        Framing.RTU: "RTU over TCP (transparent gateway)",
                        Framing.TCP: "Modbus TCP",
                    }
                ),
                vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): cv.positive_int,
            }
        )
        return self.async_show_form(step_id="tcp", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZehnderOptionsFlow:
        """Create the options flow handler."""
        # config_entry is set automatically by Home Assistant (2024.12+)
        return ZehnderOptionsFlow()


class ZehnderOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing Zehnder EVO Connect ModBus entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry_data = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=entry_data.get(CONF_SCAN_INTERVAL, 10),
                ): vol.All(cv.positive_int, vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_FILTER_SCAN_INTERVAL,
                    default=entry_data.get(
                        CONF_FILTER_SCAN_INTERVAL, DEFAULT_FILTER_SCAN_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Range(min=60, max=86400)),
                vol.Required(
                    CONF_WORD_ORDER, default=entry_data.get(CONF_WORD_ORDER, DEFAULT_WORD_ORDER)
                ): vol.In(
                    {
                        WordOrder.BIG: "Big endian (A B C D)",
                        WordOrder.LITTLE: "Little endian word swap (C D A B)",
                    }
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
