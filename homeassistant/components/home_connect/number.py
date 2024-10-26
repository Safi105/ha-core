"""Provides number enties for Home Connect."""

import logging

from homeconnect.api import HomeConnectError

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ConfigEntryAuth
from .const import ATTR_CONSTRAINTS, ATTR_STEPSIZE, ATTR_UNIT, ATTR_VALUE, DOMAIN
from .entity import HomeConnectEntity

_LOGGER = logging.getLogger(__name__)


NUMBERS = (
    NumberEntityDescription(
        key="Refrigeration.FridgeFreezer.Setting.SetpointTemperatureRefrigerator",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="refrigerator_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.FridgeFreezer.Setting.SetpointTemperatureFreezer",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="freezer_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.BottleCooler.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="bottle_cooler_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.ChillerLeft.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="chiller_left_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.ChillerCommon.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="chiller_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.ChillerRight.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="chiller_right_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.WineCompartment.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="wine_compartment_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.WineCompartment2.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="wine_compartment_2_setpoint_temperature",
    ),
    NumberEntityDescription(
        key="Refrigeration.Common.Setting.WineCompartment3.SetpointTemperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="wine_compartment_3_setpoint_temperature",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Home Connect number."""

    def get_entities() -> list[HomeConnectNumberEntity]:
        """Get a list of entities."""
        hc_api: ConfigEntryAuth = hass.data[DOMAIN][config_entry.entry_id]
        return [
            HomeConnectNumberEntity(device, description)
            for description in NUMBERS
            for device in hc_api.devices
            if description.key in device.appliance.status
        ]

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class HomeConnectNumberEntity(HomeConnectEntity, NumberEntity):
    """Number setting class for Home Connect."""

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value of the entity."""
        _LOGGER.debug(
            "Tried to set value %s to %s for %s",
            value,
            self.bsh_key,
            self.entity_id,
        )
        try:
            await self.hass.async_add_executor_job(
                self.device.appliance.set_setting,
                self.bsh_key,
                value,
            )
        except HomeConnectError as err:
            _LOGGER.error(
                "Error setting value %s to %s for %s: %s",
                value,
                self.bsh_key,
                self.entity_id,
                err,
            )

    async def async_fetch_constraints(self) -> None:
        """Fetch the max and min values and step for the number entity."""
        try:
            data = await self.hass.async_add_executor_job(
                self.device.appliance.get, f"/settings/{self.bsh_key}"
            )
        except HomeConnectError as err:
            _LOGGER.error("An error occurred: %s", err)
            return
        if not data or not (constraints := data.get(ATTR_CONSTRAINTS)):
            return
        self._attr_native_max_value = constraints.get(ATTR_MAX)
        self._attr_native_min_value = constraints.get(ATTR_MIN)
        self._attr_native_step = constraints.get(ATTR_STEPSIZE)
        self._attr_native_unit_of_measurement = data.get(ATTR_UNIT)

    async def async_update(self) -> None:
        """Update the number setting status."""
        if not (data := self.device.appliance.status.get(self.bsh_key)):
            _LOGGER.error("No value for %s", self.bsh_key)
            self._attr_native_value = None
            return
        self._attr_native_value = data.get(ATTR_VALUE, None)
        _LOGGER.debug("Updated, new value: %s", self._attr_native_value)

        if (
            not hasattr(self, "_attr_native_min_value")
            or self._attr_native_min_value is None
            or not hasattr(self, "_attr_native_max_value")
            or self._attr_native_max_value is None
            or not hasattr(self, "_attr_native_step")
            or self._attr_native_step is None
        ):
            await self.async_fetch_constraints()