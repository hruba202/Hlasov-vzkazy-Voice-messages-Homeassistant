from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, MAX_FILES

class InboxEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self.source = entry.data["source"]
        self._attr_unique_id = f"{self.source}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self.source)},
            name=f"Vzkazy {self.source}", manufacturer="Voice Inbox", model="HTTP přijímač")

    @property
    def extra_state_attributes(self):
        return {"source": self.source, "quota_scope": "all_sources", "limit": MAX_FILES}
