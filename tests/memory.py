"""Shared fake Modbus register memory used by the tests.

Address values are 0-based protocol addresses (4xxxx - 40001).
"""

from __future__ import annotations


def _float(value: float) -> list[int]:
    """Encode a float32 into two big-endian word-order registers."""
    import struct

    return list(struct.unpack(">HH", struct.pack(">f", value)))


def build_memory() -> dict[int, int]:
    """Return a realistic register memory map for an EVO 2 with both heaters."""
    memory: dict[int, int] = {
        # Status block 40101-40103
        100: 0,  # RF communication OK
        101: 0,
        102: 0,  # fault status: fan ok
        # Sensor block 41000-41027
        999: 2,  # current fan speed: 2 (medium)
        1000: 0,
        1001: 0,
        1002: 0,  # error code: none
        1003: 30,  # countdown: 30 min
        # 41005-41006 extraction temperature 20.0 C
        1004: _float(20.0)[0],
        1005: _float(20.0)[1],
        # 41007-41008 outdoor temperature 5.0 C
        1006: _float(5.0)[0],
        1007: _float(5.0)[1],
        # 41009-41010 discharge temperature 10.0 C
        1008: _float(10.0)[0],
        1009: _float(10.0)[1],
        # 41011-41012 supply temperature 18.5 C
        1010: _float(18.5)[0],
        1011: _float(18.5)[1],
        1012: 0,  # preheater off
        1013: 0,  # filter ok
        1014: 0,  # no defrost
        1015: 100,  # bypass 100 %
        1016: 45,  # indoor humidity 45 %
        1017: 0xEF,  # outdoor humidity unavailable
        # 41019-41020 supply airflow 120 m3/h
        1018: _float(120.0)[0],
        1019: _float(120.0)[1],
        # 41021-41022 extract airflow 118 m3/h
        1020: _float(118.0)[0],
        1021: _float(118.0)[1],
        1022: 90,  # air quality
        1023: 0x03,  # AQ basis: VOC + CO2
        1024: 650,  # CO2 650 ppm
        1025: 0xEF,  # afterheater unavailable
        1026: 0x0003,  # capabilities: preheater + afterheater available
        # Filter block 41040-41042
        1039: 40,  # days remaining
        1040: 90,  # interval
        1041: 44,  # usage %
        # Required speed 41500 = 3 (medium)
        1499: 3,
        # Configuration block 42001-42016
        2000: 20,  # standby supply
        2001: 20,  # standby extract
        2002: 40,  # speed1 supply
        2003: 40,  # speed1 extract
        2004: 70,  # speed2 supply
        2005: 70,  # speed2 extract
        2006: 95,  # speed3 supply
        2007: 95,  # speed3 extract
        # 42009-42010 frost protection setpoint 0.0 C
        2008: _float(0.0)[0],
        2009: _float(0.0)[1],
        # 42011-42012 preheater setpoint 0.0 C
        2010: _float(0.0)[0],
        2011: _float(0.0)[1],
        # 42013-42014 afterheater setpoint 5.0 C
        2012: _float(5.0)[0],
        2013: _float(5.0)[1],
        # 42015-42016 afterheater differential 3.0 K
        2014: _float(3.0)[0],
        2015: _float(3.0)[1],
    }
    return memory


SERIAL_CONFIG = {
    "connection_type": "serial",
    "serial_port": "/dev/ttyFAKE",
    "baudrate": 9600,
    "parity": "N",
    "stopbits": 1,
    "bytesize": 8,
    "slave_id": 1,
}
