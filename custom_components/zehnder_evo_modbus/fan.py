"""Fan platform for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging
from typing import ClassVar

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .entity import ZehnderEntity
from .registers import PRESET_ORDER, PRESET_TO_SPEED, SPEED_TO_PRESET

_LOGGER = logging.getLogger(__name__)

ORDERED_NON_OFF_PRESETS: list[str] = list(PRESET_ORDER[1:])


class ZehnderFan(ZehnderEntity, FanEntity):
    """Ventilation control for the Zehnder EVO unit (register 41500)."""

    _attr_name = None  # Device-named primary entity
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes: ClassVar[list[str]] = list(PRESET_ORDER)
    _attr_translation_key = "ventilation"

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator, entry_id, "ventilation")

    @property
    def available(self) -> bool:
        """Available when the required speed register is readable."""
        return super().available and self._value("required_speed") is not None

    @property
    def is_on(self) -> bool | None:
        """Return True when ventilation is not off."""
        speed = self._value("required_speed")
        if speed is None:
            return None
        return speed != 0

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset (from register 41500)."""
        speed = self._value("required_speed")
        if speed is None:
            return None
        return SPEED_TO_PRESET.get(int(speed))

    @property
    def percentage(self) -> int | None:
        """Map the ordered presets to a percentage for the UI slider."""
        speed = self._value("required_speed")
        if speed is None:
            return None
        preset = SPEED_TO_PRESET.get(int(speed))
        if preset is None or preset == "off":
            return None
        return ordered_list_item_to_percentage(ORDERED_NON_OFF_PRESETS, preset)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the required ventilation speed."""
        speed = PRESET_TO_SPEED[preset_mode]
        await self.coordinator.async_write_required_speed(speed)

    async def async_set_percentage(self, percentage: int) -> None:
        """Map a percentage back to the nearest preset."""
        preset = percentage_to_ordered_list_item(ORDERED_NON_OFF_PRESETS, percentage)
        await self.async_set_preset_mode(preset)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Zehnder EVO fan entity."""
    coordinator = entry.runtime_data
    async_add_entities([ZehnderFan(coordinator, entry.entry_id)])
