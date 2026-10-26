from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from .const import DOMAIN, MAX_FILES
from .entity import InboxEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN].coordinator
    async_add_entities([LastMessage(coordinator, entry), Count(coordinator, entry), Usage(coordinator, entry)])

class LastMessage(InboxEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "last_message", "Poslední vzkaz")
    @property
    def native_value(self):
        return self.coordinator.data.get("latest", {}).get(self.source, {}).get("time")
    @property
    def extra_state_attributes(self):
        info = self.coordinator.data.get("latest", {}).get(self.source, {})
        return {"source": self.source, "file": info.get("file"),
                "media_content_id": info.get("media_content_id"), "time_basis": "file_modified_utc"}

class Count(InboxEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "vzkazů"
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "total_count", "Počet vzkazů celkem")
    @property
    def native_value(self):
        return self.coordinator.data["count"]

class Usage(InboxEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "quota_usage", "Zaplnění společné kvóty")
    @property
    def native_value(self):
        return round(self.coordinator.data["count"] * 100 / MAX_FILES, 1)
