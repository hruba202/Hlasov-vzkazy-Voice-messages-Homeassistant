"""One config entry per source. Only the SHA256 digest of its random key is stored."""
import re
import probatio as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .access import valid_network
from .const import DOMAIN
from .storage import key_digest, valid_source

class VoiceInboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            source = user_input["source"]
            if not valid_source(source):
                errors["source"] = "invalid_source"
            if not valid_network(user_input["network"]):
                errors["network"] = "invalid_network"
            if not re.fullmatch(r"[0-9a-f]{64}", user_input["key"]):
                errors["key"] = "invalid_key"
            elif any(entry.data.get("key_digest") == key_digest(user_input["key"])
                     for entry in self._async_current_entries()):
                errors["key"] = "duplicate_key"
            if not errors:
                await self.async_set_unique_id(source)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=source, data={
                    "source": source, "network": user_input["network"],
                    "key_digest": key_digest(user_input["key"]),
                })
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("source"): str,
            vol.Required("network"): str,
            vol.Required("key"): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        }), errors=errors)
