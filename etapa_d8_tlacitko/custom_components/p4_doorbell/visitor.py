"""One physical press, one action. No replay on HA reconnect or startup."""
import asyncio
import time


class VisitorButton:
    def __init__(self, controller):
        self.c = controller
        self.last_press = -float("inf")
        self.handling = False
        self.task = None

    def observe(self, entity, old, new, context):
        selected = self.c.mailbox.options.get("visitor_sensor")
        if not selected or entity != selected or old is None or new is None:
            return
        if old.state != "off" or new.state != "on":
            return
        if self.task is not None and not self.task.done():
            return
        self.task = self.c.hass.async_create_task(self.press(context))

    async def press(self, context):
        if self.handling or time.monotonic() - self.last_press < 1:
            return
        self.last_press = time.monotonic()
        self.handling = True
        try:
            mailbox = self.c.mailbox
            if not self.c.door_idle():
                return  # Never hang up or change a ringing/active call.
            if mailbox.phase == "waiting_button" and mailbox.busy:
                mailbox.confirm_recording()
            elif mailbox.phase == "recording" and mailbox.busy:
                o = mailbox.options
                if mailbox.value(o.get("record_status", "")).startswith("Nahravam"):
                    save = o.get("save_button")
                    if not save:
                        self.c.status = "Chybí nastavení tlačítka Vzkaz zastavit a ulozit."
                        return
                    mailbox.phase = "uploading"
                    await self.c.service("button", "press", {"entity_id": save}, context)
            elif mailbox.busy or self.c.lock.locked():
                return  # Ignore presses during prompt/start/upload/cancellation.
            else:
                busy_entity = mailbox.options.get("record_busy")
                if busy_entity and mailbox.value(busy_entity) != "off":
                    return
                await self.c.ring(context)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.c.status = "Stisk zvonku: " + (str(exc) or type(exc).__name__)[:800]
        finally:
            self.handling = False
