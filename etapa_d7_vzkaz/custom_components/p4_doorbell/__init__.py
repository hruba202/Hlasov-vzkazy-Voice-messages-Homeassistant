"""First doorbell UI over existing VoIP; no firmware or private VoIP imports."""
import asyncio
import logging
from pathlib import Path
from aiohttp import web
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from .controller import Controller, DoorbellError
from .mailbox import Mailbox, MailboxError

DOMAIN = "p4_doorbell"
PLATFORMS = [Platform.BUTTON, Platform.SENSOR]
LOGGER = logging.getLogger(__name__)


class View(HomeAssistantView):
    url = "/api/p4_doorbell/control"
    name = "api:p4_doorbell:control"
    requires_auth = True
    cors_allowed = False

    def __init__(self, hass, runtime):
        self.hass, self.runtime = hass, runtime

    def controller(self, request):
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            raise web.HTTPUnauthorized()
        controller = self.runtime.get("controller")
        if controller is None:
            raise web.HTTPServiceUnavailable()
        return controller

    async def get(self, request):
        controller = self.controller(request)
        return web.json_response({**controller.snapshot(), "module_url": self.runtime.get("module_url")},
                                 headers={"Cache-Control": "no-store"})

    async def post(self, request):
        controller = self.controller(request)
        if request.content_length is None or request.content_length > 4096:
            return web.json_response({"error": "Příliš velký požadavek."}, status=413)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError()
            action = data.get("action")
            context = self.context(request)
            if action == "enroll":
                await controller.enroll(context)
            elif action == "ring":
                await controller.ring(context)
            elif action == "message":
                controller.mailbox.start(context)
            elif action == "cancel_message":
                await controller.mailbox.cancel(context)
            elif action == "reply":
                values = [data.get(k) for k in ("device_id", "visit", "call_id")]
                if not all(isinstance(v, str) and 0 < len(v) <= 256 for v in values):
                    raise ValueError()
                await controller.reply(*values, context)
            else:
                raise ValueError()
            return web.json_response({"status": controller.status})
        except (ValueError, TypeError):
            return web.json_response({"error": "Neplatný požadavek."}, status=400)
        except (DoorbellError, MailboxError) as exc:
            return web.json_response({"error": str(exc)}, status=409)
        except HomeAssistantError as exc:
            detail = str(exc).strip() or type(exc).__name__
            key = getattr(exc, "translation_key", None)
            if key and key not in detail:
                detail += f" [{key}]"
            controller.status = "HA odmítl akci: " + detail[:1000]
            LOGGER.warning("Doorbell action rejected: %s", controller.status)
            return web.json_response({"error": controller.status}, status=503)
        except TimeoutError:
            controller.status = "Vypršel čas pro potvrzení akce. Ověř připojení P4 a stav hovoru."
            LOGGER.warning("Doorbell action timed out")
            return web.json_response({"error": controller.status}, status=503)


async def async_setup(hass, config):
    runtime = hass.data.setdefault(DOMAIN, {"controller": None, "lock": asyncio.Lock()})
    async with runtime["lock"]:
        if not runtime.get("view_registered"):
            hass.http.register_view(View(hass, runtime))
            runtime["view_registered"] = True
        if not runtime.get("static_registered"):
            await hass.http.async_register_static_paths([StaticPathConfig(
                "/p4_doorbell_static/panel.js", str(Path(__file__).parent / "panel.js"), False)])
            runtime["static_registered"] = True
    return True


async def async_setup_entry(hass, entry):
    runtime = hass.data[DOMAIN]
    async with runtime["lock"]:
        runtime["controller"] = Controller(hass, entry)
        controller = runtime["controller"]
        controller.mailbox = Mailbox(controller)
        @callback
        def state_changed(event):
            controller.mailbox.observe(event.data.get("entity_id"),
                                       event.data.get("old_state"), event.data.get("new_state"))
        entry.async_on_unload(hass.bus.async_listen("state_changed", state_changed))
        # Reuse EXACTLY the upstream resource URL: different query strings could
        # create a second page-level audio engine in the same browser tab.
        lovelace = hass.data.get("lovelace")
        resources = getattr(lovelace, "resources", None)
        if resources is not None:
            await resources.async_get_info()
            runtime["module_url"] = next((item["url"] for item in resources.async_items()
                if item.get("url", "").split("?")[0] == "/voip-stack/voip-stack-card.js"), None)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        if not frontend.async_panel_exists(hass, "p4-doorbell"):
            await panel_custom.async_register_panel(hass, frontend_url_path="p4-doorbell",
                webcomponent_name="p4-doorbell-panel", sidebar_title="Dveřní zvonek",
                sidebar_icon="mdi:doorbell-video", module_url="/p4_doorbell_static/panel.js?v=0.2.0",
                require_admin=True)

    async def ring_service(call):
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if not user or not user.is_admin:
                raise ServiceValidationError("První testovací verze je pro správce HA.")
        try:
            await runtime["controller"].ring(call.context)
        except (DoorbellError, MailboxError) as exc:
            raise ServiceValidationError(str(exc)) from None

    hass.services.async_register(DOMAIN, "ring", ring_service)
    async def message_service(call):
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if not user or not user.is_admin:
                raise ServiceValidationError("Tato verze je určena správci HA.")
        try:
            if call.service == "cancel_message":
                await controller.mailbox.cancel(call.context)
            else:
                controller.mailbox.start(call.context)
        except MailboxError as exc:
            raise ServiceValidationError(str(exc)) from None
    hass.services.async_register(DOMAIN, "leave_message", message_service)
    hass.services.async_register(DOMAIN, "cancel_message", message_service)
    return True


async def async_unload_entry(hass, entry):
    runtime = hass.data[DOMAIN]
    controller = runtime.get("controller")
    state = controller.state(controller.config["door_state"]) if controller else None
    active = state and state.state.lower() not in ("idle", "unknown", "unavailable")
    if controller and (controller.lock.locked() or controller.mailbox.busy or active):
        return False
    async with runtime["lock"]:
        if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            return False
        runtime["controller"] = None
        controller.mailbox.disarm()
        hass.services.async_remove(DOMAIN, "ring")
        hass.services.async_remove(DOMAIN, "leave_message")
        hass.services.async_remove(DOMAIN, "cancel_message")
        frontend.async_remove_panel(hass, "p4-doorbell")
    return True
