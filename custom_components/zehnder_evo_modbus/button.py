"""Button platform for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .entity import ZehnderEntity

_LOGGER = logging.getLogger(__name__)

FILTER_RESET_DESCRIPTION = ButtonEntityDescription(
    key="filter_timer_reset",
    name="Reset filter timer",
    icon="mdi:air-filter",
)


class ZehnderFilterResetButton(ZehnderEntity, ButtonEntity):
    """Button that resets the air filter service timer (register 42000)."""

    entity_description: ButtonEntityDescription

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the button."""
        super().__init__(
            coordinator,
            entry_id,
            FILTER_RESET_DESCRIPTION.key,
            FILTER_RESET_DESCRIPTION.name,
        )
        self.entity_description = FILTER_RESET_DESCRIPTION

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_reset_filter_timer()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Zehnder EVO buttons."""
    coordinator = entry.runtime_data
    async_add_entities([ZehnderFilterResetButton(coordinator, entry.entry_id)])
