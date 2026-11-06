"""Tests for the Modbus client wrapper (version compatibility shims)."""


import pytest

from custom_components.zehnder_evo_modbus import modbus_client
from custom_components.zehnder_evo_modbus.const import (
    CONF_CONNECTION_TYPE,
    CONF_FRAMING,
    CONF_HOST,
    CONF_SERIAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONF_TCP,
    CONF_TCP_PORT,
)
from custom_components.zehnder_evo_modbus.modbus_client import (
    ZehnderModbusClient,
    ZehnderModbusError,
)


class FakePymodbusClient:
    """Fake pymodbus client with the legacy `slave` keyword."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.connected = True
        self.registers = {}

    async def connect(self):
        return True

    def close(self):
        return None

    async def read_holding_registers(self, address, count=None, slave=None):
        return FakeResult([self.registers.get(address + i, 0) for i in range(count)])

    async def write_register(self, address, value, slave=None):
        self.registers[address] = value
        return FakeResult([])

    async def write_registers(self, address, values, slave=None):
        for i, value in enumerate(values):
            self.registers[address + i] = value
        return FakeResult([])


class FakePymodbusClientDeviceId(FakePymodbusClient):
    """Fake pymodbus client using the new `device_id` keyword."""

    async def read_holding_registers(self, address, count=None, device_id=None):
        return FakeResult([self.registers.get(address + i, 0) for i in range(count)])

    async def write_register(self, address, value, device_id=None):
        self.registers[address] = value
        return FakeResult([])


class FakeResult:
    def __init__(self, registers, error=False):
        self.registers = registers
        self._error = error

    def isError(self):
        return self._error


def _serial_config():
    return {
        CONF_CONNECTION_TYPE: CONF_SERIAL,
        CONF_SERIAL_PORT: "/dev/ttyFAKE",
        CONF_SLAVE_ID: 1,
    }


def _tcp_config():
    return {
        CONF_CONNECTION_TYPE: CONF_TCP,
        CONF_HOST: "1.2.3.4",
        CONF_TCP_PORT: 502,
        CONF_FRAMING: "rtu",
        CONF_SLAVE_ID: 3,
    }


async def test_serial_client_uses_slave_kwarg(monkeypatch):
    created = {}

    def fake_serial_factory(**kwargs):
        created["kwargs"] = kwargs
        return FakePymodbusClient(**kwargs)

    monkeypatch.setattr(modbus_client, "AsyncModbusSerialClient", fake_serial_factory)
    client = ZehnderModbusClient(_serial_config())
    assert await client.async_connect() is True
    assert created["kwargs"]["port"] == "/dev/ttyFAKE"

    registers = await client.async_read_holding(1499, 1)
    assert registers == [0]

    await client.async_write_register(1499, 5)
    assert client._client.registers[1499] == 5


async def test_client_supports_device_id_kwarg(monkeypatch):
    monkeypatch.setattr(
        modbus_client, "AsyncModbusSerialClient", lambda **kw: FakePymodbusClientDeviceId(**kw)
    )
    client = ZehnderModbusClient({**_serial_config(), CONF_SLAVE_ID: 7})
    assert await client.async_connect() is True
    assert client._id_kwarg == "device_id"


async def test_tcp_client_build(monkeypatch):
    created = {}

    def fake_tcp_factory(**kwargs):
        created["kwargs"] = kwargs
        return FakePymodbusClient(**kwargs)

    monkeypatch.setattr(modbus_client, "AsyncModbusTcpClient", fake_tcp_factory)
    client = ZehnderModbusClient(_tcp_config())
    assert await client.async_connect() is True
    assert created["kwargs"]["host"] == "1.2.3.4"
    assert created["kwargs"]["port"] == 502
    assert "framer" in created["kwargs"]


async def test_error_response_raises(monkeypatch):
    class ErroringClient(FakePymodbusClient):
        async def read_holding_registers(self, address, count=None, slave=None):
            return FakeResult([], error=True)

    monkeypatch.setattr(
        modbus_client, "AsyncModbusSerialClient", lambda **kw: ErroringClient(**kw)
    )
    client = ZehnderModbusClient(_serial_config())
    await client.async_connect()
    with pytest.raises(ZehnderModbusError):
        await client.async_read_holding(100, 3)


async def test_connection_failure_returns_false(monkeypatch):
    class FailingClient(FakePymodbusClient):
        async def connect(self):
            raise OSError("no route to host")

    monkeypatch.setattr(
        modbus_client, "AsyncModbusSerialClient", lambda **kw: FailingClient(**kw)
    )
    client = ZehnderModbusClient(_serial_config())
    assert await client.async_connect() is False
