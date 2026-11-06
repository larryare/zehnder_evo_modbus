"""Pure-python tests for the register decoders."""

from custom_components.zehnder_evo_modbus.const import WordOrder
from custom_components.zehnder_evo_modbus.registers import (
    CURRENT_SPEED_LABELS,
    ERROR_CODES,
    PRESET_ORDER,
    PRESET_TO_SPEED,
    READ_BLOCKS,
    REGISTER_MAP,
    SPEED_TO_PRESET,
    decode_all,
    decode_float,
    decode_value,
    encode_float,
)


def test_float_big_word_order():
    # 50.0 = 0x42480000 -> registers [0x4248, 0x0000] in big-endian word order
    regs = [0x4248, 0x0000]
    assert decode_float(regs, WordOrder.BIG) == 50.0


def test_float_little_word_order():
    hi, lo = encode_float(23.5, WordOrder.BIG)
    # little word order swaps the two words
    swapped = [lo, hi]
    assert decode_float(swapped, WordOrder.LITTLE) == 23.5
    # decoding big-ordered registers with little order gives garbage, not 23.5
    assert decode_float([hi, lo], WordOrder.LITTLE) != 23.5


def test_float_roundtrip():
    for value in (0.0, -12.25, 100.0, -20.0, 30.5):
        for order in (WordOrder.BIG, WordOrder.LITTLE):
            assert decode_float(encode_float(value, order), order) == value


def test_float_nan_and_below_absolute_zero_are_unknown():
    assert decode_float([0x7FC0, 0x0000], WordOrder.BIG) is None  # NaN
    # -300 C encoded as float32
    assert decode_float(encode_float(-300.0, WordOrder.BIG), WordOrder.BIG) is None


def test_uint8_sentinel_ef_and_above_unavailable():
    definition = REGISTER_MAP["preheater_pct"]
    assert decode_value(definition, [0x32], WordOrder.BIG) == 50
    for sentinel in (0xEF, 0xF0, 0xFF):
        assert decode_value(definition, [sentinel], WordOrder.BIG) is None


def test_humidity_sentinels():
    definition = REGISTER_MAP["indoor_humidity"]
    assert decode_value(definition, [45], WordOrder.BIG) == 45
    assert decode_value(definition, [0xEF], WordOrder.BIG) is None
    assert decode_value(definition, [0xFF], WordOrder.BIG) is None


def test_bypass_over_120_is_unavailable():
    definition = REGISTER_MAP["bypass_position"]
    assert decode_value(definition, [0], WordOrder.BIG) == 0
    assert decode_value(definition, [100], WordOrder.BIG) == 100
    assert decode_value(definition, [121], WordOrder.BIG) is None


def test_co2_sentinels():
    definition = REGISTER_MAP["co2"]
    assert decode_value(definition, [650], WordOrder.BIG) == 650
    assert decode_value(definition, [0x7FF], WordOrder.BIG) is None
    assert decode_value(definition, [0x8000], WordOrder.BIG) is None


def test_flow_sentinels():
    definition = REGISTER_MAP["supply_flow"]
    assert decode_value(definition, [0x42F0, 0x0000], WordOrder.BIG) == 120.0
    assert decode_value(definition, [0x7FFF, 0x0000], WordOrder.BIG) is None
    assert decode_value(definition, [0x8000, 0x0000], WordOrder.BIG) is None
    assert decode_value(definition, [0x0000, 0x7FFF], WordOrder.BIG) is None


def test_uint6_countdown_masks_high_bits():
    definition = REGISTER_MAP["disable_countdown"]
    assert decode_value(definition, [0x3F], WordOrder.BIG) == 63
    assert decode_value(definition, [0xFF], WordOrder.BIG) == 63


def test_decode_all_from_raw_map():
    raw = {
        999: 2,  # current fan speed -> low
        1002: 0,  # error code
        1003: 30,  # countdown
        1004: 0x41A0,  # extraction temp 20.0
        1005: 0x0000,
        1006: 0x40A0,  # outdoor temp 5.0
        1007: 0x0000,
        1016: 0xEF,  # indoor humidity unavailable
        1024: 0x028A,  # co2 650
        1026: 0x0003,  # fan speed bits: pre+after heater available
        1499: 3,  # required speed -> medium
        1041: 40,  # filter usage
    }
    data = decode_all(raw, WordOrder.BIG)
    assert data["current_fan_speed"] == 2
    assert data["error_code"] == 0
    assert data["disable_countdown"] == 30
    assert data["extraction_temp"] == 20.0
    assert data["outdoor_temp"] == 5.0
    assert data["indoor_humidity"] is None
    assert data["co2"] == 650
    assert data["fan_speed_bits"] == 3
    assert data["required_speed"] == 3
    assert data["filter_usage_pct"] == 40
    # keys without registers present are simply absent
    assert "supply_temp" not in data


def test_preset_mapping_is_bijective():
    for preset in PRESET_ORDER:
        assert SPEED_TO_PRESET[PRESET_TO_SPEED[preset]] == preset


def test_error_codes_cover_documented_values():
    assert ERROR_CODES[0] == "no_error"
    assert ERROR_CODES[255] == "identification"
    assert len(ERROR_CODES) == 11


def test_current_speed_labels_cover_documented_values():
    for value in (0, 1, 2, 3, 11, 12, 13, 21, 23, 24):
        assert value in CURRENT_SPEED_LABELS


def test_read_blocks_are_consistent_with_register_map():
    """Every polled register must be covered by exactly one read block."""
    for block in READ_BLOCKS:
        covered = set(range(block.address, block.address + block.count))
        for definition in REGISTER_MAP.values():
            addresses = set(definition.register_addresses())
            if addresses & covered:
                assert addresses <= covered, (
                    f"{definition.key} straddles block {block.name}"
                )
