"""Config flow for the SkycropHD HDMI Switch Infrared integration."""

from typing import Any, override

import probatio

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
    async_get_receivers,
)
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from . import SkycropHDConfigEntry
from .const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    CONF_POWER_ON_DELAY,
    DEFAULT_POWER_ON_DELAY,
    DEFAULT_SOURCE_NAMES,
    DEVICE_NAME,
    DOMAIN,
)

OPTIONS_SCHEMA = probatio.Schema(
    {
        **{
            probatio.Required(key, default=default): TextSelector()
            for key, default in DEFAULT_SOURCE_NAMES.items()
        },
        probatio.Required(
            CONF_POWER_ON_DELAY, default=DEFAULT_POWER_ON_DELAY
        ): probatio.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=30,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement=UnitOfTime.SECONDS,
                )
            ),
            probatio.Coerce(float),
        ),
    }
)


def _infrared_schema(hass: HomeAssistant) -> probatio.Schema:
    """Return the emitter and optional receiver selection schema."""
    return probatio.Schema(
        {
            probatio.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                EntitySelectorConfig(
                    domain=INFRARED_DOMAIN,
                    include_entities=async_get_emitters(hass),
                )
            ),
            probatio.Optional(CONF_INFRARED_RECEIVER_ENTITY_ID): EntitySelector(
                EntitySelectorConfig(
                    domain=INFRARED_DOMAIN,
                    include_entities=async_get_receivers(hass),
                )
            ),
        }
    )


class SkycropHDConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for SkycropHD HDMI Switch Infrared."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle emitter and optional receiver selection."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_infrared_emitters")

        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_INFRARED_ENTITY_ID: user_input[CONF_INFRARED_ENTITY_ID]}
            )
            return self.async_create_entry(title=DEVICE_NAME, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_infrared_schema(self.hass)
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the emitter or receiver of an existing HDMI switch."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_infrared_emitters")

        entry = self._get_reconfigure_entry()
        if user_input is not None:
            emitter_entity_id = user_input[CONF_INFRARED_ENTITY_ID]
            if any(
                other.entry_id != entry.entry_id
                and other.data.get(CONF_INFRARED_ENTITY_ID) == emitter_entity_id
                for other in self._async_current_entries(include_ignore=False)
            ):
                return self.async_abort(reason="already_configured")
            # Replace the data so a cleared receiver is removed.
            return self.async_update_reload_and_abort(entry, data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _infrared_schema(self.hass), entry.data
            ),
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: SkycropHDConfigEntry,
    ) -> SkycropHDOptionsFlow:
        """Get the options flow for this handler."""
        return SkycropHDOptionsFlow()


class SkycropHDOptionsFlow(OptionsFlowWithReload):
    """Handle the input names and power-on delay of a SkycropHD HDMI switch."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the input names and the power-on delay."""
        errors: dict[str, str] = {}
        if user_input is not None:
            names = {key: user_input[key].strip() for key in DEFAULT_SOURCE_NAMES}
            if any(not name for name in names.values()):
                errors["base"] = "empty_source_name"
            elif len(set(names.values())) != len(names):
                errors["base"] = "duplicate_source_name"
            else:
                return self.async_create_entry(
                    data={
                        **names,
                        CONF_POWER_ON_DELAY: user_input[CONF_POWER_ON_DELAY],
                    }
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, user_input or self.config_entry.options
            ),
            errors=errors,
        )
