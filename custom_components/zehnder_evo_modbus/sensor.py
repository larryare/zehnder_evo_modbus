"""Sensor platform for the Zehnder EVO Connect ModBus integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .entity import ZehnderEntity
from .registers import (
    CURRENT_SPEED_LABELS,
    ERROR_CODES,
    TIMER_SPEEDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZehnderSensorDescription(SensorEntityDescription):
    """Sensor description with the register key it reads."""

    value_key: str = ""
    capability_key: str | None = None


SENSORS: tuple[ZehnderSensorDescription, ...] = (
    ZehnderSensorDescription(
        key="extraction_temp",
        value_key="extraction_temp",
        name="Extract air temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    ZehnderSensorDescription(
        key="outdoor_temp",
        value_key="outdoor_temp",
        name="Outdoor temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    ZehnderSensorDescription(
        key="discharge_temp",
        value_key="discharge_temp",
        name="Discharge air temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    ZehnderSensorDescription(
        key="supply_temp",
        value_key="supply_temp",
        name="Supply air temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    ZehnderSensorDescription(
        key="supply_flow",
        value_key="supply_flow",
        name="Supply airflow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
    ),
    ZehnderSensorDescription(
        key="extract_flow",
        value_key="extract_flow",
        name="Extract airflow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
    ),
    ZehnderSensorDescription(
        key="indoor_humidity",
        value_key="indoor_humidity",
        name="Indoor humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ZehnderSensorDescription(
        key="outdoor_humidity",
        value_key="outdoor_humidity",
        name="Outdoor humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ZehnderSensorDescription(
        key="co2",
        value_key="co2",
        name="CO\u2082 level",
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    ZehnderSensorDescription(
        key="air_quality",
        value_key="air_quality",
        name="Air quality",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:air-filter",
    ),
    ZehnderSensorDescription(
        key="preheater_pct",
        value_key="preheater_pct",
        name="Preheater power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:heating-coil",
        capability_key="preheater",
    ),
    ZehnderSensorDescription(
        key="afterheater_pct",
        value_key="afterheater_pct",
        name="Afterheater power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:heating-coil",
        capability_key="afterheater",
    ),
    ZehnderSensorDescription(
        key="bypass_position",
        value_key="bypass_position",
        name="Bypass position",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:valve",
    ),
    ZehnderSensorDescription(
        key="disable_countdown",
        value_key="disable_countdown",
        name="Speed disable countdown",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-outline",
    ),
    ZehnderSensorDescription(
        key="filter_days_remaining",
        value_key="filter_days_remaining",
        name="Filter replacement in",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
    ),
    ZehnderSensorDescription(
        key="filter_interval",
        value_key="filter_interval",
        name="Filter replacement interval",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:air-filter",
        entity_registry_enabled_default=False,
    ),
    ZehnderSensorDescription(
        key="filter_usage_pct",
        value_key="filter_usage_pct",
        name="Filter usage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:air-filter",
    ),
    ZehnderSensorDescription(
        key="current_fan_speed",
        value_key="current_fan_speed",
        name="Current fan speed",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    ZehnderSensorDescription(
        key="error_code",
        value_key="error_code",
        name="Error code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle",
    ),
    ZehnderSensorDescription(
        key="air_quality_basis",
        value_key="air_quality_basis",
        name="Air quality basis",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:format-list-bulleted",
    ),
)


class ZehnderSensor(ZehnderEntity, SensorEntity):
    """A sensor backed by one decoded register."""

    entity_description: ZehnderSensorDescription

    def __init__(self, coordinator, entry_id: str, description: ZehnderSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the decoded register value (None -> unknown)."""
        value = self._value(self.entity_description.value_key)
        if value is None:
            return None
        if self.entity_description.value_key == "disable_countdown":
            current = self._value("current_fan_speed")
            if current not in TIMER_SPEEDS:
                return None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Add human readable labels for enum-like registers."""
        if self.entity_description.value_key == "current_fan_speed":
            value = self._value("current_fan_speed")
            if isinstance(value, int):
                return {"speed": CURRENT_SPEED_LABELS.get(value, str(value))}
            return None
        if self.entity_description.value_key == "error_code":
            value = self._value("error_code")
            if isinstance(value, int):
                return {"description": ERROR_CODES.get(value, "unknown")}
            return None
        if self.entity_description.value_key == "air_quality_basis":
            value = self._value("air_quality_basis")
            if isinstance(value, int):
                return {
                    "voc": bool(value & 0x01),
                    "co2": bool(value & 0x02),
                    "humidity": bool(value & 0x04),
                }
            return None
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Zehnder EVO sensors."""
    coordinator = entry.runtime_data
    capabilities = coordinator.capabilities

    entities = []
    for description in SENSORS:
        if (
            description.capability_key is not None
            and capabilities.get("known")
            and not capabilities.get(description.capability_key)
        ):
            continue
        entities.append(ZehnderSensor(coordinator, entry.entry_id, description))
    async_add_entities(entities)
