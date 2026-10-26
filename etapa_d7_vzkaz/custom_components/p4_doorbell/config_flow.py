"""UI configuration only; no phone settings are changed during setup."""
import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector, entity_registry as er

DOMAIN = "p4_doorbell"


class DoorbellFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MailboxOptions()

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


class MailboxOptions(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            controller = self.hass.data.get(DOMAIN, {}).get("controller")
            if controller and (controller.lock.locked() or controller.mailbox.busy
                               or controller.mailbox.watching or not controller.door_idle()):
                errors["base"] = "busy"
            else:
                registry = er.async_get(self.hass)
                domains = {"record_button": "button", "cancel_button": "button",
                           "record_busy": "binary_sensor", "record_status": "sensor", "last_reason": "sensor"}
                valid = all((e := registry.async_get(user_input[key])) is not None
                            and e.device_id == self.config_entry.data["door_device"]
                            and e.domain == domain for key, domain in domains.items())
                media = user_input["prompt"]
                if (not valid or user_input["record_button"] == user_input["cancel_button"]
                        or user_input["record_status"] == user_input["last_reason"]):
                    errors["base"] = "door_entities"
                elif not str(media.get("media_content_id", "")).startswith("media-source://media_source/"):
                    errors["base"] = "local_media"
                else:
                    return self.async_create_entry(title="", data=user_input)
        schema = {
            vol.Required("auto_after_timeout", default=self.config_entry.options.get("auto_after_timeout", False)): selector.BooleanSelector(),
            vol.Required("prompt"): selector.MediaSelector(),
        }
        for key, domain in (("record_button", "button"), ("cancel_button", "button"),
                            ("record_busy", "binary_sensor"), ("record_status", "sensor"), ("last_reason", "sensor")):
            schema[vol.Required(key)] = selector.EntitySelector({"filter": {"domain": domain}})
        return self.async_show_form(step_id="init", errors=errors,
            data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), self.config_entry.options))
