"""LAN-only upload view. Never logs request headers, keys or request bodies."""
import asyncio
import logging
from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers.network import is_cloud_connection
from .access import Attempts, direct_lan
from .const import DOMAIN, EVENT_SAVED, MAX_BYTES, MAX_CONCURRENT, URL
from .storage import Rejected, Store, authenticate, metadata

LOGGER = logging.getLogger(__name__)

class Runtime:
    def __init__(self):
        self.lifecycle_lock = asyncio.Lock()
        self.browser_lock = asyncio.Lock()
        self.browser_views_registered = False
        self.browser_static_registered = False
        self.shutdown_registered = False
        self.sources = {}
        self.active = set()
        self.attempts = Attempts()
        self.store = Store()
        self.coordinator = None

    async def updated(self, source, rejected=False):
        if self.coordinator is not None:
            try:
                await self.coordinator.async_upload_finished(source, rejected)
            except Exception:
                LOGGER.error("Voice inbox entity/notification refresh failed; request details suppressed")

def error(status, code):
    return web.json_response({"error": code}, status=status)

class UploadView(HomeAssistantView):
    url = URL
    name = "api:voice_inbox:upload"
    requires_auth = False
    cors_allowed = False

    def __init__(self, hass, runtime):
        self.hass, self.runtime = hass, runtime

    async def post(self, request):
        rt = self.runtime
        peer_info = request.transport.get_extra_info("peername") if request.transport else None
        peer = peer_info[0] if peer_info else None
        remote = request.remote
        cloud = is_cloud_connection(self.hass)
        forwarded = any(k in request.headers for k in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto"))
        # Reject before reading the body or comparing keys. Do not disclose source existence.
        if not any(direct_lan(remote, peer, conf["network"], cloud, forwarded) for conf in rt.sources.values()):
            return error(401, "unauthorized")
        if rt.attempts.blocked(remote):
            return web.json_response({"error": "authentication_rate_limited"}, status=503, headers={"Retry-After": "60"})
        source = request.headers.get("X-Voice-Source", "")
        conf = rt.sources.get(source)
        key = request.headers.get("X-Voice-Key", "")
        if (not conf or not direct_lan(remote, peer, conf["network"], cloud, forwarded)
                or not authenticate(key, conf["key_digest"])):
            rt.attempts.failure(remote)
            return error(401, "unauthorized")
        return await self.receive(request, source)

    async def receive(self, request, source):
        """Shared bounded receive/commit path, called only after authorization."""
        rt = self.runtime
        if source in rt.active or len(rt.active) >= MAX_CONCURRENT:
            return error(503, "upload_busy")
        try:
            rate, mime = metadata(request.headers)
            length = request.content_length
            if length is None or length <= 0 or "Transfer-Encoding" in request.headers:
                raise Rejected(400, "content_length_required")
            if length > MAX_BYTES:
                raise Rejected(413, "body_too_large")
        except Rejected as exc:
            return error(exc.status, exc.code)
        rt.active.add(source)
        try:
            body = bytearray()
            async with asyncio.timeout(30):
                async for chunk in request.content.iter_chunked(65536):
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise Rejected(413, "body_too_large")
                    body.extend(chunk)
            if len(body) != length:
                raise Rejected(400, "incomplete_body")
            # Shield the disk commit: client cancellation must not release the source
            # lock while an executor job still owns the buffer / partial file.
            future = self.hass.async_add_executor_job(rt.store.save, source, bytes(body), rate, mime)
            try:
                saved = await asyncio.shield(future)
            except asyncio.CancelledError:
                try:
                    saved = await asyncio.shield(future)
                    self.hass.bus.async_fire(EVENT_SAVED, saved)
                    await rt.updated(source)
                except Rejected:
                    pass
                raise
            self.hass.bus.async_fire(EVENT_SAVED, saved)
            await rt.updated(source)
            return web.json_response(saved, status=201)
        except Rejected as exc:
            if exc.code == "file_quota_reached":
                await rt.updated(source, rejected=True)
            return error(exc.status, exc.code)
        except (TimeoutError, ConnectionError, web.HTTPBadRequest):
            return error(400, "incomplete_or_timed_out_upload")
        except Exception:
            # No exception text/traceback: third-party exceptions can contain secrets.
            LOGGER.error("Voice inbox upload failed internally; request details suppressed")
            return error(503, "upload_unavailable")
        finally:
            rt.active.discard(source)
