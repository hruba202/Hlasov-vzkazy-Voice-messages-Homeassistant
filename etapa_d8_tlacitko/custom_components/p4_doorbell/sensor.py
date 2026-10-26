from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([StatusSensor(hass.data["p4_doorbell"]["controller"], entry)], True)


class StatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Stav ovládání"

    def __init__(self, controller, entry):
        self.controller = controller
        self._attr_unique_id = entry.entry_id + "_status"
        self._attr_device_info = DeviceInfo(identifiers={("p4_doorbell", entry.entry_id)}, name="Dveřní zvonek")

    async def async_update(self):
        self._attr_native_value = self.controller.status[:255]
        self._attr_extra_state_attributes = {"group": self.controller.group}
