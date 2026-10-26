"""Shared read-only inventory and quota notices; never deletes recordings."""
from datetime import timedelta
import logging
from homeassistant.components import persistent_notification
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, MAX_FILES

LOGGER = logging.getLogger(__name__)
NOTICE_ID = "voice_inbox_quota"

class InboxCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, store):
        # Shared inventory must not inherit the first entry's lifecycle/context.
        super().__init__(hass, LOGGER, config_entry=None, name=DOMAIN,
                         update_interval=timedelta(seconds=60))
        self.store = store
        self.warned = False
        self.last_notice_count = None

    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(self.store.snapshot)
        except OSError as exc:
            raise UpdateFailed("Cannot read voice inbox inventory") from exc
        count = data["count"]
        if count * 100 >= MAX_FILES * 80:
            if not self.warned:
                self.hass.bus.async_fire("voice_inbox_quota_warning", {"count": count, "limit": MAX_FILES})
            if count != self.last_notice_count:
                persistent_notification.async_create(self.hass,
                    f"Uloženo {count} z {MAX_FILES} hlasových vzkazů. "
                    "Po zaplnění budou nové uploady odmítnuty (507). Nic se automaticky nemaže.",
                    title="Hlasové vzkazy: zaplnění úložiště", notification_id=NOTICE_ID)
            self.warned = True
            self.last_notice_count = count
        elif self.warned:
            persistent_notification.async_dismiss(self.hass, NOTICE_ID)
            self.warned = False
            self.last_notice_count = None
        return data

    async def async_upload_finished(self, source, rejected=False):
        # Refresh failure must not turn an already committed WAV's 201 into 503.
        await self.async_refresh()
        if rejected:
            count = (self.data or {}).get("count")
            self.hass.bus.async_fire("voice_inbox_quota_rejected", {
                "source": source, "count": count, "limit": MAX_FILES,
                "reason": "file_quota_reached", "inventory_available": self.last_update_success})
            persistent_notification.async_create(self.hass,
                f"Vzkaz ze zdroje {source} nebyl uložen: byla dosažena kvóta {MAX_FILES} WAV. "
                "Přijímač vrátil 507. Nic nebylo smazáno. Nový vzkaz není v HA uložen.",
                title="Hlasové vzkazy: upload odmítnut", notification_id=NOTICE_ID)
            self.warned = True
