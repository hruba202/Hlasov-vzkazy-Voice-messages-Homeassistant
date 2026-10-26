"""Administrator-only recorder UI; independent of the LAN device upload API."""
from pathlib import Path
from aiohttp import web
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from .const import MAX_FILES
from .http import UploadView, error
from .storage import Rejected

PANEL = "voice-inbox"


def administrator(request):
    user = request.get("hass_user")
    return user is not None and user.is_admin


class BrowserUploadView(UploadView):
    url = "/api/voice_inbox/browser/upload"
    name = "api:voice_inbox:browser_upload"
    requires_auth = True

    async def post(self, request):
        if not administrator(request):
            return error(401, "administrator_required")
        source = request.headers.get("X-Voice-Source", "")
        if source not in self.runtime.sources:
            return error(400, "unknown_source")
        return await self.receive(request, source)


class BrowserStateView(BrowserUploadView):
    url = "/api/voice_inbox/browser/state"
    name = "api:voice_inbox:browser_state"
    post = None

    async def get(self, request):
        if not administrator(request):
            return error(401, "administrator_required")
        try:
            state = await self.hass.async_add_executor_job(self.runtime.store.snapshot)
        except OSError:
            return error(503, "storage_unavailable")
        latest = {source: {**item, "time": item["time"].isoformat()}
                  for source, item in state["latest"].items()
                  if source in self.runtime.sources}
        return web.json_response({"sources": sorted(self.runtime.sources),
                                  "count": state["count"], "limit": MAX_FILES,
                                  "latest": latest}, headers={"Cache-Control": "no-store"})


class BrowserAudioView(BrowserUploadView):
    url = "/api/voice_inbox/browser/audio/{source}/{filename}"
    name = "api:voice_inbox:browser_audio"
    post = None

    async def get(self, request, source, filename):
        if not administrator(request):
            return error(401, "administrator_required")
        if source not in self.runtime.sources:
            return error(400, "unknown_source")
        try:
            body = await self.hass.async_add_executor_job(
                self.runtime.store.read_audio, source, filename)
        except Rejected as exc:
            return error(exc.status, exc.code)
        return web.Response(body=body, content_type="audio/wav",
                            headers={"Cache-Control": "no-store"})


async def async_register_browser(hass, runtime):
    async with runtime.browser_lock:
        if not runtime.browser_views_registered:
            for view in (BrowserUploadView, BrowserStateView, BrowserAudioView):
                hass.http.register_view(view(hass, runtime))
            runtime.browser_views_registered = True
        if not runtime.browser_static_registered:
            await hass.http.async_register_static_paths([
                StaticPathConfig("/voice_inbox_static/recorder.js",
                                 str(Path(__file__).parent / "recorder.js"), False)])
            runtime.browser_static_registered = True
        if not frontend.async_panel_exists(hass, PANEL):
            await panel_custom.async_register_panel(
                hass, frontend_url_path=PANEL, webcomponent_name="voice-inbox-panel",
                sidebar_title="Hlasové vzkazy", sidebar_icon="mdi:microphone-message",
                module_url="/voice_inbox_static/recorder.js?v=0.3.1", require_admin=True)
