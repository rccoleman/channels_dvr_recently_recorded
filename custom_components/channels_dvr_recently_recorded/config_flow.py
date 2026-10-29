"""Config flow for the Channels DVR Recently Recorded."""
from custom_components.channels_dvr_recently_recorded.api import (
    ChannelsDVR,
    ConnectionFail,
    DEFAULT_PORT,
)
from custom_components.channels_dvr_recently_recorded import DOMAIN
from custom_components.channels_dvr_recently_recorded.sensor import (
    CONF_DL_IMAGES,
    CONF_HOSTNAME,
    CONF_IMG_DIR,
    CONF_MAX,
    CONF_VERIFICATION,
    DEFAULT_NAME,
)
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

STEP_DISCOVERY_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MAX, default=5): cv.string,
        vol.Optional(CONF_DL_IMAGES, default=True): cv.boolean,
        vol.Optional(CONF_IMG_DIR, default="/upcoming-media-card-images/"): cv.string,
    },
    extra=vol.PREVENT_EXTRA,
)

STEP_USER_DATA_SCHEMA = STEP_DISCOVERY_DATA_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST, default="localhost"): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
    },
    extra=vol.PREVENT_EXTRA,
)


async def validate_input(data):
    """Validate the user input allows us to connect."""

    channels_dvr = ChannelsDVR(data[CONF_HOST], data[CONF_PORT])

    try:
        auth = await channels_dvr.get_auth()
    except ConnectionFail:
        raise CannotConnect

    return {CONF_VERIFICATION: auth.get(CONF_VERIFICATION, "None")}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Channels DVR."""

    async def _try_create_entry(self, data):
        data.update(await validate_input(data))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=data[CONF_HOST], data=data)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            # Config entry already exists, only one allowed.
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:
            data = user_input.copy()

            try:
                return await self._try_create_entry(data)
            except CannotConnect:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(self, discovery_info):
        """Handle a flow initialized by zeroconf discovery."""
        _LOGGER.debug(f"Discovered {discovery_info}")

        if isinstance(discovery_info, dict):
            host: str = discovery_info[CONF_HOST]
            port: int = discovery_info[CONF_PORT]
            hostname: str = discovery_info[CONF_HOSTNAME]
        else:
            host: str = discovery_info.host
            port: int = discovery_info.port
            hostname: str = discovery_info.hostname

        self._discovered = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_HOSTNAME: hostname,
        }

        _LOGGER.debug(f"Host={host}, Port={port}, Hostname={hostname}")

        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured({CONF_HOSTNAME: hostname})

        self.context.update({"title_placeholders": self._discovered})

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle confirmation flow for discovered Channels DVR instance"""

        errors = {}

        if user_input is not None:
            try:
                data = user_input.copy()
                data.update(self._discovered)

                return await self._try_create_entry(data)
            except CannotConnect:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="confirm",
            data_schema=STEP_DISCOVERY_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
