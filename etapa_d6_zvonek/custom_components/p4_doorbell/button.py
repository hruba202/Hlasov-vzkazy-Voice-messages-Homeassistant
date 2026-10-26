from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from .controller import DoorbellError
from homeassistant.exceptions import HomeAssistantError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RingButton(hass.data["p4_doorbell"]["controller"], entry)])


class RingButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Zazvonit"
    _attr_icon = "mdi:doorbell"

    def __init__(self, controller, entry):
        self.controller = controller
        self._attr_unique_id = entry.entry_id + "_ring"
        self._attr_device_info = DeviceInfo(identifiers={("p4_doorbell", entry.entry_id)}, name="Dveřní zvonek")

    async def async_press(self):
        try:
            await self.controller.ring(self._context)
        except DoorbellError as exc:
            raise HomeAssistantError(str(exc)) from None
