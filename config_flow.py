"""Config flow for Drea integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
DATA_SCHEMA = vol.Schema(
    {
        vol.Required("five_finger"): str,
    }
)

SUPPORTED_DOMAINS = [
    "light",
    "media_player",
    "climate"
]


class SimpleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Drea."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user")

        return self.async_create_entry(title=DOMAIN, data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.drea_options: dict[str, Any] = {}

    async def async_step_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if user_input is not None:
            user_input.update(self.drea_options)
            return self.async_create_entry(title="", data=user_input)

        data_schema = {}

        if self.drea_options.get("five_finger_opt") is not None:
            attributes = _async_get_attributes_by_entity(self.hass, self.drea_options.get("five_finger_opt"))
            data_schema[vol.Required("five_finger_attr", default=self.config_entry.options.get("five_finger_attr"))] = SelectSelector(
                SelectSelectorConfig(options=attributes, mode=SelectSelectorMode.DROPDOWN)
            )

        if self.drea_options.get("four_finger_opt") is not None:
            attributes = _async_get_attributes_by_entity(self.hass, self.drea_options.get("four_finger_opt"))
            data_schema[vol.Required("four_finger_attr", default=self.config_entry.options.get("four_finger_attr"))] = SelectSelector(
                SelectSelectorConfig(options=attributes, mode=SelectSelectorMode.DROPDOWN)
            )

        if self.drea_options.get("three_finger_opt") is not None:
            attributes = _async_get_attributes_by_entity(self.hass, self.drea_options.get("three_finger_opt"))
            data_schema[vol.Required("three_finger_attr", default=self.config_entry.options.get("three_finger_attr"))] = SelectSelector(
                SelectSelectorConfig(options=attributes, mode=SelectSelectorMode.DROPDOWN)
            )

        if self.drea_options.get("two_finger_opt") is not None:
            attributes = _async_get_attributes_by_entity(self.hass, self.drea_options.get("two_finger_opt"))
            data_schema[vol.Required("two_finger_attr", default=self.config_entry.options.get("two_finger_attr"))] = SelectSelector(
                SelectSelectorConfig(options=attributes, mode=SelectSelectorMode.DROPDOWN)
            )

        return self.async_show_form(
            step_id="attribute",
            data_schema=vol.Schema(data_schema),
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        if user_input is not None:
            self.drea_options.update(user_input)
            return await self.async_step_attribute()

        supported_entities = _async_get_entities_by_filter(self.hass, SUPPORTED_DOMAINS)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "five_finger_opt",
                        default=self.config_entry.options.get("five_finger_opt"),
                    ): EntitySelector(EntitySelectorConfig(include_entities=supported_entities)),
                    vol.Optional(
                        "four_finger_opt",
                        default=self.config_entry.options.get("four_finger_opt"),
                    ): EntitySelector(EntitySelectorConfig(include_entities=supported_entities)),
                    vol.Optional(
                        "three_finger_opt",
                        default=self.config_entry.options.get("three_finger_opt"),
                    ): EntitySelector(EntitySelectorConfig(include_entities=supported_entities)),
                    vol.Optional(
                        "two_finger_opt",
                        default=self.config_entry.options.get("two_finger_opt"),
                    ): EntitySelector(EntitySelectorConfig(include_entities=supported_entities)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


def _async_get_entities_by_filter(
        hass: HomeAssistant,
        domains: list[str] | None = None,
) -> list[str]:
    """Fetch all entities or entities in the given domains."""
    list = []
    for state in hass.states.async_all(domains and set(domains)):
        list.append(state.entity_id)
    return list


def _async_get_attributes_by_entity(
        hass: HomeAssistant,
        entity_id: str
)-> list[str]:
    """Fetch all entities or entities in the given domains."""
    entity_dict = hass.states.get(entity_id).as_dict()
    attr_keys = entity_dict.get("attributes").keys()

    domain = entity_id.split(".", 2)[0]

    attr_list = []

    if domain == "light":
        attr_list.append("brightness")
        if "hs" in entity_dict.get("attributes").get("supported_color_modes") or "xy" in entity_dict.get("attributes").get("supported_color_modes") or "rgb" in entity_dict.get("attributes").get("supported_color_modes"):
            attr_list.append("color")
            attr_list.append("saturation")
        if "color_temp" in entity_dict.get("attributes").get("supported_color_modes"):
            attr_list.append("color_temp")
        if "rgbw" in entity_dict.get("attributes").get("supported_color_modes"):
            attr_list.append("rgbw_color")

    elif domain == "climate":
        if "temperature" in attr_keys:
            attr_list.append("temperature")

    elif domain == "media_player":
        if "volume_level" in attr_keys:
            attr_list.append("volume_level")

    return list(attr_list)
