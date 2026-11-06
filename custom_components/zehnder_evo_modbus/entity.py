"""Shared entity base class for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import ZehnderEvoCoordinator


class ZehnderEntity(CoordinatorEntity[ZehnderEvoCoordinator]):
    """Base for all entities of this integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZehnderEvoCoordinator,
        entry_id: str,
        key: str,
        name: str | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        if name is not None:
            self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info of the EVO bridge."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        """Entity is available when the last update succeeded and had data."""
        return super().available and bool(self.coordinator.data)

    def _value(self, key: str) -> Any:
        """Return the decoded value for a register key."""
        return (self.coordinator.data or {}).get(key)
