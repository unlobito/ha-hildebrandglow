"""Platform for sensor integration."""
from typing import Any, Callable

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_POWER,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
    VOLUME_CUBIC_METERS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, GLOW_SESSION
from .glow import Glow

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="gas_consumption",
        name="Gas Consumption",
        native_unit_of_measurement=VOLUME_CUBIC_METERS,
        device_class=DEVICE_CLASS_GAS,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="power_consumption",
        name="Power Consumption",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="energy_consumption",
        name="Energy Consumption",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        GlowSensorEntity(
            glow=hass.data[DOMAIN][config.entry_id][GLOW_SESSION],
            description=description,
        )
        for description in SENSORS
    )


class GlowSensorEntity(SensorEntity):
    """Sensor object for the Glowmarkt resource's current consumption."""

    should_poll = False

    glow: Glow

    def __init__(
        self,
        *,
        glow: Glow,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.glow = glow

        self.entity_id = f"{SENSOR_DOMAIN}.glow{glow.hardwareId}_{description.key}"
        self.entity_description = description
        self._attr_unique_id = f"glow{glow.hardwareId}_{description.key}"

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"glow{glow.hardwareId}")},
            manufacturer="Hildebrand",
            name="Smart Meter",
        )

    async def async_added_to_hass(self) -> None:
        """Register callback function."""
        self.glow.register_on_message_callback(self.on_message)

    def on_message(self, message: Any) -> None:
        """Receive callback for incoming MQTT payloads."""
        self.hass.add_job(self.async_write_ha_state)

    @property
    def available(self) -> bool:
        """Return the sensor's availability."""
        return getattr(self.glow.data, self.entity_description.key) is not None

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        value = getattr(self.glow.data, self.entity_description.key)
        if isinstance(value, str):
            return value.lower()
        return value
