"""Binary sensor platform for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .entity import ZehnderEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZehnderBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description with the register key it reads."""

    value_key: str = ""


BINARY_SENSORS: tuple[ZehnderBinarySensorDescription, ...] = (
    ZehnderBinarySensorDescription(
        key="dirty_filter",
        value_key="dirty_filter",
        name="Dirty filter",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    ZehnderBinarySensorDescription(
        key="defrost_active",
        value_key="defrost_active",
        name="Defrosting",
        icon="mdi:snowflake-melt",
    ),
    ZehnderBinarySensorDescription(
        key="fan_fault",
        value_key="fault_status",
        name="Fan fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ZehnderBinarySensorDescription(
        key="rf_comm_lost",
        value_key="rf_comm_status",
        name="RF communication lost",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


class ZehnderBinarySensor(ZehnderEntity, BinarySensorEntity):
    """A binary sensor backed by one decoded register."""

    entity_description: ZehnderBinarySensorDescription

    def __init__(
        self,
        coordinator,
        entry_id: str,
        description: ZehnderBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, description.key, description.name)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return True when the register reports the alarm/active state."""
        value = self._value(self.entity_description.value_key)
        if value is None:
            return None
        if self.entity_description.key == "rf_comm_lost":
            return value == 1
        return value == 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Zehnder EVO binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        ZehnderBinarySensor(coordinator, entry.entry_id, description)
        for description in BINARY_SENSORS
    )
