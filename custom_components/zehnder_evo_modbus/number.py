"""Number platform for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import ZehnderEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZehnderNumberDef:
    """Definition of a writable value."""

    key: str
    name: str
    address: int
    count: int
    min: float
    max: float
    step: float
    unit: str | None
    icon: str
    write_only: bool = False
    mode: NumberMode = NumberMode.BOX


NUMBERS: tuple[ZehnderNumberDef, ...] = (
    ZehnderNumberDef(
        key="disable_speed1_time",
        name="Disable speed 1 for",
        address=1500,
        count=1,
        min=0,
        max=1080,
        step=1,
        unit=UnitOfTime.MINUTES,
        icon="mdi:timer-off-outline",
        write_only=True,
    ),
    ZehnderNumberDef(
        key="disable_speed2_time",
        name="Disable speed 2 for",
        address=1501,
        count=1,
        min=0,
        max=1080,
        step=1,
        unit=UnitOfTime.MINUTES,
        icon="mdi:timer-off-outline",
        write_only=True,
    ),
    ZehnderNumberDef(
        key="disable_speed3_time",
        name="Disable speed 3 for",
        address=1502,
        count=1,
        min=0,
        max=1080,
        step=1,
        unit=UnitOfTime.MINUTES,
        icon="mdi:timer-off-outline",
        write_only=True,
    ),
    ZehnderNumberDef(
        key="standby_supply_pct",
        name="Standby speed supply",
        address=2000,
        count=1,
        min=0,
        max=40,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-chevron-down",
    ),
    ZehnderNumberDef(
        key="standby_extract_pct",
        name="Standby speed extraction",
        address=2001,
        count=1,
        min=0,
        max=40,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-chevron-down",
    ),
    ZehnderNumberDef(
        key="speed1_supply_pct",
        name="Speed 1 supply airflow",
        address=2002,
        count=1,
        min=0,
        max=80,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-low-speed",
    ),
    ZehnderNumberDef(
        key="speed1_extract_pct",
        name="Speed 1 extraction airflow",
        address=2003,
        count=1,
        min=0,
        max=80,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-low-speed",
    ),
    ZehnderNumberDef(
        key="speed2_supply_pct",
        name="Speed 2 supply airflow",
        address=2004,
        count=1,
        min=0,
        max=100,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-medium-speed",
    ),
    ZehnderNumberDef(
        key="speed2_extract_pct",
        name="Speed 2 extraction airflow",
        address=2005,
        count=1,
        min=10,
        max=100,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-medium-speed",
    ),
    ZehnderNumberDef(
        key="speed3_supply_pct",
        name="Speed 3 supply airflow",
        address=2006,
        count=1,
        min=0,
        max=100,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-high-speed",
    ),
    ZehnderNumberDef(
        key="speed3_extract_pct",
        name="Speed 3 extraction airflow",
        address=2007,
        count=1,
        min=10,
        max=100,
        step=1,
        unit=PERCENTAGE,
        icon="mdi:fan-high-speed",
    ),
    ZehnderNumberDef(
        key="frost_setpoint",
        name="Frost protection setpoint",
        address=2008,
        count=2,
        min=-20,
        max=50,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake-thermometer",
    ),
    ZehnderNumberDef(
        key="preheat_setpoint",
        name="Preheater setpoint",
        address=2010,
        count=2,
        min=-20,
        max=50,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-plus",
    ),
    ZehnderNumberDef(
        key="afterheat_setpoint",
        name="Afterheater setpoint",
        address=2012,
        count=2,
        min=0,
        max=30,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
    ),
    ZehnderNumberDef(
        key="afterheat_diff",
        name="Afterheater differential",
        address=2014,
        count=2,
        min=1,
        max=10,
        step=0.1,
        unit="K",
        icon="mdi:thermometer-lines",
    ),
)


class ZehnderNumber(ZehnderEntity, RestoreEntity, NumberEntity):
    """A number backed by a (writable) register."""

    def __init__(self, coordinator, entry_id: str, definition: ZehnderNumberDef) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry_id, definition.key, definition.name)
        self._def = definition
        self._attr_native_min_value = definition.min
        self._attr_native_max_value = definition.max
        self._attr_native_step = definition.step
        self._attr_native_unit_of_measurement = definition.unit
        self._attr_mode = definition.mode
        if definition.write_only:
            self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Restore the last value for write-only entities."""
        await super().async_added_to_hass()
        if not self._def.write_only:
            return
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (None, "unknown", "unavailable"):
            return
        try:
            self._attr_native_value = float(last_state.state)
        except ValueError:
            _LOGGER.debug("Could not restore state for %s", self.entity_id)

    @property
    def native_value(self) -> float | None:
        """Return the current value from the coordinator."""
        if self._def.write_only:
            return getattr(self, "_attr_native_value", None)
        value = self._value(self._def.key)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the device."""
        if self._def.count == 1:
            await self.coordinator.async_write_register(self._def.address, int(value))
        else:
            await self.coordinator.async_write_float(self._def.address, value)
        if self._def.write_only:
            self._attr_native_value = value
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Zehnder EVO numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        ZehnderNumber(coordinator, entry.entry_id, definition)
        for definition in NUMBERS
    )
