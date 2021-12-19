"""The Hildebrand Glow integration."""
import asyncio
from typing import Any, Dict

import async_timeout
import voluptuous as vol
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    InvalidStateError,
)

from .const import APP_ID, DOMAIN, GLOW_SESSION, LOGGER
from .glow import CannotConnect, Glow, InvalidAuth, NoCADAvailable

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = (SENSOR_DOMAIN,)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Hildebrand Glow component."""
    hass.data[DOMAIN] = {}

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hildebrand Glow from a config entry."""
    glow = Glow(
        APP_ID,
        entry.data["username"],
        entry.data["password"],
    )

    try:
        if not await async_connect_or_timeout(hass, glow):
            return False
    except CannotConnect as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {GLOW_SESSION: glow}

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    return True


async def async_connect_or_timeout(hass: HomeAssistant, glow: Glow) -> bool:
    """Connect from Glow."""
    try:
        async with async_timeout.timeout(10):
            LOGGER.debug("Initialize connection from Glow")

            await hass.async_add_executor_job(glow.authenticate)
            await hass.async_add_executor_job(glow.retrieve_cad_hardwareId)
            await hass.async_add_executor_job(glow.connect_mqtt)

            while not glow.broker_active:
                await asyncio.sleep(1)
    except InvalidAuth as err:
        LOGGER.error("Couldn't login with the provided username/password")
        raise ConfigEntryAuthFailed from err

    except NoCADAvailable as err:
        LOGGER.error("Couldn't find any CAD devices (e.g. Glow Stick)")
        raise InvalidStateError from err

    except asyncio.TimeoutError as err:
        await async_disconnect_or_timeout(hass, glow)
        LOGGER.debug("Timeout expired: %s", err)
        raise CannotConnect from err

    return True


async def async_disconnect_or_timeout(hass: HomeAssistant, glow: Glow) -> bool:
    """Disconnect from Glow."""
    LOGGER.debug("Disconnect from Glow")
    async with async_timeout.timeout(3):
        await hass.async_add_executor_job(glow.disconnect)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Hildebrand Glow config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator[GLOW_SESSION].disconnect()
    return unload_ok
