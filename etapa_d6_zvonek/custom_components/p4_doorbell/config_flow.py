"""UI configuration only; no phone settings are changed during setup."""
import probatio as vol
from homeassistant import config_entries
from homeassistant.helpers import selector, entity_registry as er

DOMAIN = "p4_doorbell"


class DoorbellFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors = {}
        if user_input is not None:
            registry = er.async_get(self.hass)
            # All physical door entities must belong to the same existing ESP.
            entries = [registry.async_get(user_input[k]) for k in ("camera", "player", "door_state")]
            if not all(e and e.device_id == user_input["door_device"] for e in entries):
                errors["base"] = "door_entities"
            elif not 1 <= len(set(user_input["receivers"])) <= 3:
                errors["base"] = "receiver_count"
            else:
                self._data = dict(user_input)
                return await self.async_step_reply()
        return self.async_show_form(step_id="user", errors=errors, data_schema=vol.Schema({
            vol.Required("door_device"): selector.DeviceSelector({"filter": {"integration": "esphome"}}),
            vol.Required("door_name", default="ESP32-P4"): selector.TextSelector(),
            vol.Required("camera"): selector.EntitySelector({"filter": {"domain": "camera"}}),
            vol.Required("player"): selector.EntitySelector({"filter": {"domain": "media_player"}}),
            vol.Required("door_state"): selector.EntitySelector({"filter": {"domain": "sensor"}}),
            vol.Required("receivers"): selector.DeviceSelector({"filter": {"integration": "voip_stack"}, "multiple": True}),
        }))

    async def async_step_reply(self, user_input=None):
        errors = {}
        if user_input is not None:
            media = user_input["reply"]
            if not str(media.get("media_content_id", "")).startswith("media-source://media_source/"):
                errors["base"] = "local_media"
            else:
                self._data.update(user_input)
                await self.async_set_unique_id("doorbell")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Dveřní zvonek P4", data=self._data)
        return self.async_show_form(step_id="reply", errors=errors, data_schema=vol.Schema({
            vol.Required("reply_label", default="Právě nemůžeme otevřít"): selector.TextSelector(),
            vol.Required("reply"): selector.MediaSelector(),
        }))
