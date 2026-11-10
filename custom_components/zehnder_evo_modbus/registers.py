"""Register map, decoders and encoders for the Zehnder EVO Connect ModBus bridge.

This module is pure Python (no Home Assistant imports) so the register
handling can be unit tested in isolation.

Register numbers from the official manual use the 5-digit PLC convention
(4xxxx). The Modbus protocol address (0-based) is ``4xxxx - 40001``.
Registers 40000-42016 are supported by the device; all of them are
holding registers (read via FC03, write via FC06/FC16).
"""

from __future__ import annotations

import math
import struct
from collections.abc import Callable
from dataclasses import dataclass

from .const import WordOrder


class RegisterDef:
    """Definition of a single logical register (possibly 2 words)."""

    __slots__ = ("address", "count", "dtype", "key", "unavailable")

    def __init__(
        self,
        key: str,
        address: int,
        count: int = 1,
        dtype: str = "uint16",
        unavailable: Callable[[list[int]], bool] | None = None,
    ) -> None:
        self.key = key
        self.address = address
        self.count = count
        self.dtype = dtype
        self.unavailable = unavailable

    def register_addresses(self) -> range:
        """Return the 0-based protocol addresses covered by this definition."""
        return range(self.address, self.address + self.count)


# ---------------------------------------------------------------------------
# Sentinel ("special value") checks. Values documented as unavailable or as
# sensor errors are reported as None (unknown) by the integration.
# ---------------------------------------------------------------------------


def _low_byte(regs: list[int]) -> int:
    return regs[0] & 0xFF


def _uint8_unavailable(regs: list[int]) -> bool:
    """EFh and above: not available / sensor error (0xEF..0xFF)."""
    return _low_byte(regs) >= 0xEF


def _humidity_unavailable(regs: list[int]) -> bool:
    """EFh = unavailable, F0h-FFh = sensor error."""
    return _low_byte(regs) >= 0xEF


def _bypass_unavailable(regs: list[int]) -> bool:
    """Values above 120 % indicate a fault."""
    return _low_byte(regs) > 120


def _co2_unavailable(regs: list[int]) -> bool:
    """7FFh = unavailable, 8000h-FFFFh = sensor error."""
    return regs[0] >= 0x7FF


def _flow_unavailable(regs: list[int]) -> bool:
    """7FFFh = unavailable, 8000h-85FFh = sensor error."""
    for reg in regs:
        if reg == 0x7FFF or 0x8000 <= reg <= 0x85FF:
            return True
    return False


REGISTER_MAP: dict[str, RegisterDef] = {
    d.key: d
    for d in (
        # Status block 40101-40103
        RegisterDef("rf_comm_status", 100, 1, "uint16"),
        RegisterDef("fault_status", 102, 1, "uint8"),
        # Sensor block 41000-41027
        RegisterDef("current_fan_speed", 999, 1, "uint8"),
        RegisterDef("error_code", 1002, 1, "uint8"),
        RegisterDef("disable_countdown", 1003, 1, "uint6"),
        RegisterDef("extraction_temp", 1004, 2, "float"),
        RegisterDef("outdoor_temp", 1006, 2, "float"),
        RegisterDef("discharge_temp", 1008, 2, "float"),
        RegisterDef("supply_temp", 1010, 2, "float"),
        RegisterDef("preheater_pct", 1012, 1, "uint8", _uint8_unavailable),
        RegisterDef("dirty_filter", 1013, 1, "uint8"),
        RegisterDef("defrost_active", 1014, 1, "uint8"),
        RegisterDef("bypass_position", 1015, 1, "uint8", _bypass_unavailable),
        RegisterDef("indoor_humidity", 1016, 1, "uint8", _humidity_unavailable),
        RegisterDef("outdoor_humidity", 1017, 1, "uint8", _humidity_unavailable),
        RegisterDef("supply_flow", 1018, 2, "float", _flow_unavailable),
        RegisterDef("extract_flow", 1020, 2, "float", _flow_unavailable),
        RegisterDef("air_quality", 1022, 1, "uint8", _uint8_unavailable),
        RegisterDef("air_quality_basis", 1023, 1, "uint8"),
        RegisterDef("co2", 1024, 1, "uint16", _co2_unavailable),
        RegisterDef("afterheater_pct", 1025, 1, "uint8", _uint8_unavailable),
        RegisterDef("fan_speed_bits", 1026, 1, "uint16"),
        # Filter block 41040-41042 (reading 41040 triggers a slow RF query)
        RegisterDef("filter_days_remaining", 1039, 1, "uint16"),
        RegisterDef("filter_interval", 1040, 1, "uint16"),
        RegisterDef("filter_usage_pct", 1041, 1, "uint8"),
        # Required fan speed 41500 (read/write)
        RegisterDef("required_speed", 1499, 1, "uint8"),
        # Configuration block 42001-42016 (read/write)
        RegisterDef("standby_supply_pct", 2000, 1, "uint8"),
        RegisterDef("standby_extract_pct", 2001, 1, "uint8"),
        RegisterDef("speed1_supply_pct", 2002, 1, "uint8"),
        RegisterDef("speed1_extract_pct", 2003, 1, "uint8"),
        RegisterDef("speed2_supply_pct", 2004, 1, "uint8"),
        RegisterDef("speed2_extract_pct", 2005, 1, "uint8"),
        RegisterDef("speed3_supply_pct", 2006, 1, "uint8"),
        RegisterDef("speed3_extract_pct", 2007, 1, "uint8"),
        RegisterDef("frost_setpoint", 2008, 2, "float"),
        RegisterDef("preheat_setpoint", 2010, 2, "float"),
        RegisterDef("afterheat_setpoint", 2012, 2, "float"),
        RegisterDef("afterheat_diff", 2014, 2, "float"),
    )
}

# Write-only registers (cache: NO in the manual) that are not polled.
WRITE_ONLY_REGISTERS: dict[str, int] = {
    "disable_speed1_time": 1500,  # 41501, minutes, UINT6
    "disable_speed2_time": 1501,  # 41502, minutes, UINT6
    "disable_speed3_time": 1502,  # 41503, minutes, UINT6
}

FILTER_TIMER_RESET_ADDRESS = 1999  # 42000, write 0 to reset


@dataclass(frozen=True)
class ReadBlock:
    """A contiguous block of registers read with a single FC03 request."""

    name: str
    address: int
    count: int
    slow: bool = False


READ_BLOCKS: tuple[ReadBlock, ...] = (
    ReadBlock("status", 100, 3),  # 40101-40103
    ReadBlock("sensors", 999, 28),  # 41000-41027
    ReadBlock("required", 1499, 1),  # 41500
    ReadBlock("config", 2000, 16),  # 42001-42016
    ReadBlock("filter", 1039, 3, slow=True),  # 41040-41042
)

SENSOR_BLOCK_ADDRESS = 999  # 41000
SENSOR_BLOCK_COUNT = 28  # 41000-41027


def decode_float(regs: list[int], word_order: WordOrder) -> float | None:
    """Decode a 32-bit IEEE 754 float spread over two 16-bit registers.

    Returns None for NaN (documented as "no known value") and for
    values below -273 °C (documented as sensor problem).
    """
    ordered = [regs[1], regs[0]] if word_order == WordOrder.LITTLE else regs
    payload = struct.pack(">HH", ordered[0] & 0xFFFF, ordered[1] & 0xFFFF)
    value = struct.unpack(">f", payload)[0]
    if math.isnan(value) or value < -273.15:
        return None
    return value


def encode_float(value: float, word_order: WordOrder) -> list[int]:
    """Encode a float as two 16-bit registers with the given word order."""
    payload = struct.pack(">f", float(value))
    hi, lo = struct.unpack(">HH", payload)
    return [lo, hi] if word_order == WordOrder.LITTLE else [hi, lo]


# Floats within these ranges and not denormal-tiny are considered plausible
# sensor readings when auto-detecting the float word order.
_TEMP_RANGE = (-60.0, 120.0)
_FLOW_RANGE = (0.0, 2000.0)
_DENORMAL_LIMIT = 1e-6


def _float_is_plausible(
    regs: list[int], word_order: WordOrder, value_range: tuple[float, float]
) -> bool:
    """Return True if regs decode to a believable number in word_order."""
    value = decode_float(regs, word_order)
    if value is None:
        return False
    if value == 0.0:
        return True
    low, high = value_range
    if not low <= value <= high:
        return False
    # A wrong word order usually yields denormal-tiny or huge values.
    return abs(value) > _DENORMAL_LIMIT


def detect_word_order(sensor_block: list[int]) -> WordOrder | None:
    """Detect the float word order from a sensor block (41000-41027).

    Votes over the four air temperatures and two airflows. Returns None
    when the data is inconclusive (e.g. all sensors unavailable or 0.0).
    """
    if len(sensor_block) < SENSOR_BLOCK_COUNT:
        return None
    float_fields = (
        (5, _TEMP_RANGE),  # extraction temperature
        (7, _TEMP_RANGE),  # outdoor temperature
        (9, _TEMP_RANGE),  # discharge temperature
        (11, _TEMP_RANGE),  # supply temperature
        (19, _FLOW_RANGE),  # supply airflow
        (21, _FLOW_RANGE),  # extract airflow
    )
    votes: dict[WordOrder, int] = {WordOrder.BIG: 0, WordOrder.LITTLE: 0}
    for offset, value_range in float_fields:
        regs = sensor_block[offset : offset + 2]
        for order in (WordOrder.BIG, WordOrder.LITTLE):
            if _float_is_plausible(regs, order, value_range):
                votes[order] += 1
    if votes[WordOrder.BIG] == votes[WordOrder.LITTLE]:
        return None
    return max(votes, key=lambda order: votes[order])


def decode_value(
    definition: RegisterDef, regs: list[int], word_order: WordOrder
) -> int | float | None:
    """Decode raw registers for one definition; None means unavailable."""
    if definition.unavailable and definition.unavailable(regs):
        return None
    if definition.dtype == "float":
        return decode_float(regs, word_order)
    if definition.dtype == "uint8":
        return regs[0] & 0xFF
    if definition.dtype == "uint6":
        return regs[0] & 0x3F
    return regs[0] & 0xFFFF


def decode_all(
    raw: dict[int, int], word_order: WordOrder
) -> dict[str, int | float | None]:
    """Decode every definition present in a raw address -> register map."""
    data: dict[str, int | float | None] = {}
    for definition in REGISTER_MAP.values():
        try:
            regs = [raw[address] for address in definition.register_addresses()]
        except KeyError:
            continue
        data[definition.key] = decode_value(definition, regs, word_order)
    return data


# ---------------------------------------------------------------------------
# Fan speed mapping for register 41500 (required speed).
# ---------------------------------------------------------------------------

FAN_OFF = 0
FAN_AWAY = 1
FAN_SPEED1 = 2
FAN_SPEED2 = 3
FAN_SPEED3 = 4
FAN_AUTO = 5
FAN_BOOST = 7

PRESET_TO_SPEED: dict[str, int] = {
    "off": FAN_OFF,
    "away": FAN_AWAY,
    "low": FAN_SPEED1,
    "medium": FAN_SPEED2,
    "high": FAN_SPEED3,
    "auto": FAN_AUTO,
    "boost": FAN_BOOST,
}
SPEED_TO_PRESET: dict[int, str] = {v: k for k, v in PRESET_TO_SPEED.items()}
PRESET_ORDER: tuple[str, ...] = (
    "off",
    "away",
    "low",
    "medium",
    "high",
    "auto",
    "boost",
)

# Values reported by 41000 (current fan speed).
CURRENT_SPEED_LABELS: dict[int, str] = {
    0: "off",
    1: "low",
    2: "medium",
    3: "high",
    11: "timer_speed1_disabled",
    12: "timer_speed2_disabled",
    13: "timer_speed3_disabled",
    21: "away",
    23: "boost",
    24: "auto",
}
TIMER_SPEEDS = frozenset({11, 12, 13})

# Fallback: derive the fan preset from 41000 when 41500 is not readable
# (some bridges answer the required-speed read with a busy/acknowledge
# exception until it has been written at least once).
CURRENT_TO_PRESET: dict[int, str] = {
    0: "off",
    1: "low",
    2: "medium",
    3: "high",
    11: "low",
    12: "medium",
    13: "high",
    21: "away",
    23: "boost",
    24: "auto",
}

# Error codes for register 41003.
ERROR_CODES: dict[int, str] = {
    0: "no_error",
    1: "unspecified",
    2: "emergency_stop",
    3: "fan1_power",
    4: "x22_sensor",
    5: "x23_sensor",
    6: "x21_sensor",
    7: "x20_sensor",
    8: "fan2",
    254: "connection_mode",
    255: "identification",
}

# Capability bits for register 41027.
CAP_PREHEATER = 1 << 0
CAP_AFTERHEATER = 1 << 1
