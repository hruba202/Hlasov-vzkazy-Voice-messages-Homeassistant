"""Voice inbox: LAN uploads and an authenticated administrator recorder panel."""
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from .const import DOMAIN
from .http import Runtime, UploadView
from .storage import Store, select_media_directory
from .coordinator import InboxCoordinator
from .browser import async_register_browser, PANEL
from homeassistant.components import frontend

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

async def async_setup_entry(hass, entry):
    try:
        media_id, media_path = select_media_directory(hass.config.media_dirs)
    except ValueError as exc:
        raise ConfigEntryNotReady(str(exc)) from None
    if DOMAIN not in hass.data:
        runtime = Runtime()
        runtime.store = Store(media_path / "vzkazy", media_id)
        runtime.coordinator = InboxCoordinator(hass, runtime.store)
        hass.data[DOMAIN] = runtime
        hass.http.register_view(UploadView(hass, runtime))
    runtime = hass.data[DOMAIN]
    # HA sets up multiple source entries concurrently at startup.
    async with runtime.lifecycle_lock:
        if not runtime.shutdown_registered:
            await runtime.coordinator.async_register_shutdown()
            runtime.shutdown_registered = True
        await runtime.coordinator.async_refresh()
        if not runtime.coordinator.last_update_success:
            raise ConfigEntryNotReady("Cannot read voice inbox inventory")
        await async_register_browser(hass, runtime)
        source = entry.data["source"]
        runtime.sources[source] = dict(entry.data)
        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except BaseException:
            runtime.sources.pop(source, None)
            await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
            if not runtime.sources:
                frontend.async_remove_panel(hass, PANEL)
            raise
    return True

async def async_unload_entry(hass, entry):
    runtime = hass.data[DOMAIN]
    source = entry.data["source"]
    async with runtime.lifecycle_lock:
        if source in runtime.active:
            return False
        # Block new uploads while unloading; restore authorization if unload fails.
        conf = runtime.sources.pop(source, None)
        try:
            unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        except BaseException:
            if conf is not None:
                runtime.sources[source] = conf
            raise
        if not unloaded:
            if conf is not None:
                runtime.sources[source] = conf
            return False
        if not runtime.sources:
            frontend.async_remove_panel(hass, PANEL)
    return True
