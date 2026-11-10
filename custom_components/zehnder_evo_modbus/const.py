"""Constants for the Zehnder EVO Connect ModBus integration."""

from enum import StrEnum

DOMAIN = "zehnder_evo_modbus"
MANUFACTURER = "Zehnder"
MODEL = "EVO Connect ModBus (EVO 2/3/4)"
DEVICE_NAME = "Zehnder EVO"

CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL = "serial"
CONF_TCP = "tcp"

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_BYTESIZE = "bytesize"

CONF_HOST = "host"
CONF_TCP_PORT = "tcp_port"
CONF_FRAMING = "framing"

CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FILTER_SCAN_INTERVAL = "filter_scan_interval"
CONF_WORD_ORDER = "word_order"
CONF_ADDRESSING = "addressing"


class WordOrder(StrEnum):
    """Modbus float word order."""

    BIG = "big"
    LITTLE = "little"


class Addressing(StrEnum):
    """How 4xxxx register numbers map to protocol addresses.

    PLC: protocol address = 4xxxx - 40001 (standard, as documented in the
    Zehnder manual). DIRECT: protocol address = 4xxxx as-is (used by some
    gateways and simulators).
    """

    PLC = "plc"
    DIRECT = "direct"


class Framing(StrEnum):
    """TCP transport framing."""

    RTU = "rtu"
    TCP = "tcp"


DEFAULT_BAUDRATE = 9600
DEFAULT_PARITY = "N"
DEFAULT_STOPBITS = 1
DEFAULT_BYTESIZE = 8
DEFAULT_TCP_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_FILTER_SCAN_INTERVAL = 3600
DEFAULT_WORD_ORDER = WordOrder.BIG
DEFAULT_ADDRESSING = Addressing.PLC

DEFAULT_DEVICE_NAME = DEVICE_NAME

# Options that can be changed after initial setup, with their defaults.
DEFAULTS_BY_KEY: dict[str, object] = {
    CONF_SLAVE_ID: DEFAULT_SLAVE_ID,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_FILTER_SCAN_INTERVAL: DEFAULT_FILTER_SCAN_INTERVAL,
    CONF_WORD_ORDER: DEFAULT_WORD_ORDER,
    CONF_ADDRESSING: DEFAULT_ADDRESSING,
}
