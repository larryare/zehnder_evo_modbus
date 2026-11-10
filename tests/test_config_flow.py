"""Tests for the config flow (serial and TCP paths)."""

from contextlib import contextmanager
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.zehnder_evo_modbus.const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
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
    DOMAIN,
)
from tests.memory import SERIAL_CONFIG


class FakeValidatingClient:
    """Pretends the bridge answers."""

    def __init__(self, config):
        self.config = config

    async def async_connect(self):
        return True

    async def async_read_holding(self, address, count):
        return [0] * count

    async def async_close(self):
        return None


class FakeFailingClient(FakeValidatingClient):
    async def async_connect(self):
        return False


@contextmanager
def _patched_client(cls=FakeValidatingClient):
    """Patch the client class in the config flow AND the setup path.

    The setup path (package __init__) runs after the entry is created, and
    must not try to open real sockets in the test sandbox.
    """
    with (
        patch(
            "custom_components.zehnder_evo_modbus.config_flow.ZehnderModbusClient",
            cls,
        ),
        patch("custom_components.zehnder_evo_modbus.ZehnderModbusClient", cls),
    ):
        yield


async def test_user_flow_picks_serial(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_full_serial_flow(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONF_SERIAL}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "serial"

    with _patched_client():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_BAUDRATE: 9600,
                CONF_PARITY: "N",
                CONF_STOPBITS: 1,
                CONF_BYTESIZE: 8,
                CONF_SLAVE_ID: 1,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SERIAL_PORT] == "/dev/ttyUSB0"
    assert result["data"][CONF_SLAVE_ID] == 1
    assert result["title"] == "Zehnder EVO (/dev/ttyUSB0)"


async def test_serial_flow_connection_error(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONF_SERIAL}
    )

    with _patched_client(FakeFailingClient):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_BAUDRATE: 9600,
                CONF_PARITY: "N",
                CONF_STOPBITS: 1,
                CONF_BYTESIZE: 8,
                CONF_SLAVE_ID: 1,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "serial"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_full_tcp_flow(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONF_TCP}
    )
    assert result["step_id"] == "tcp"

    with _patched_client():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.50",
                CONF_TCP_PORT: 502,
                CONF_FRAMING: "rtu",
                CONF_SLAVE_ID: 1,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "192.168.1.50"
    assert result["title"] == "Zehnder EVO (192.168.1.50)"


async def test_duplicate_entry_aborts(hass, enable_custom_integrations):
    with _patched_client():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONNECTION_TYPE: CONF_SERIAL}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_BAUDRATE: 9600,
                CONF_PARITY: "N",
                CONF_STOPBITS: 1,
                CONF_BYTESIZE: 8,
                CONF_SLAVE_ID: 1,
            },
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # same settings again -> abort
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONNECTION_TYPE: CONF_SERIAL}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_BAUDRATE: 9600,
                CONF_PARITY: "N",
                CONF_STOPBITS: 1,
                CONF_BYTESIZE: 8,
                CONF_SLAVE_ID: 1,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass, enable_custom_integrations):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_entry = MockConfigEntry(domain=DOMAIN, data=dict(SERIAL_CONFIG))
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 30,
            "filter_scan_interval": 7200,
            CONF_WORD_ORDER: "big",
            "addressing": "plc",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_entry.options[CONF_SCAN_INTERVAL] == 30
