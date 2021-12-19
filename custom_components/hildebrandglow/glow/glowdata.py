"""Data classes for interpreted Glow structures."""

from __future__ import annotations

from dataclasses import dataclass

from . import MQTTPayload


@dataclass
class SmartMeter:
    """Data object for platform agnostic smart metering information."""

    gas_consumption: float | None

    power_consumption: int | None
    energy_consumption: float | None

    @staticmethod
    def from_mqtt_payload(data: MQTTPayload) -> SmartMeter:
        """Populate SmartMeter object from an MQTTPayload object."""
        meter = SmartMeter(
            gas_consumption=None,
            power_consumption=None,
            energy_consumption=None,
        )

        if data.gas:
            ahc = data.gas.alternative_historical_consumption
            meter.gas_consumption = ahc.current_day_consumption_delivered

        if data.electricity:
            meter.power_consumption = (
                data.electricity.historical_consumption.instantaneous_demand
            )

            if data.electricity.reading_information_set.current_summation_delivered:
                meter.energy_consumption = (
                    data.electricity.reading_information_set.current_summation_delivered
                    * data.electricity.formatting.multiplier
                    / data.electricity.formatting.divisor
                )

        return meter
