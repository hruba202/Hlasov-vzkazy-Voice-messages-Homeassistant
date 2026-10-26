from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .const import DOMAIN, MAX_FILES
from .entity import InboxEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([QuotaFull(hass.data[DOMAIN].coordinator, entry)])

class QuotaFull(InboxEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "quota_full", "Společná kvóta plná")
    @property
    def is_on(self):
        return self.coordinator.data["count"] >= MAX_FILES
