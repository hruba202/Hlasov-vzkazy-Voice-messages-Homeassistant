"""Opt-in missed-call workflow using the existing D5 recorder entities.

Never hangs up a call. A fresh, observed timeout is required for automatic use.
"""
import asyncio
import time
from datetime import datetime, timezone


class MailboxError(Exception):
    pass


class Mailbox:
    def __init__(self, controller):
        self.c = controller
        self.task = None
        self.phase = "idle"
        self.watch = None
        self.play_seen = self.record_seen = self.saved = False
        self.interrupted = self.record_requested = False
        self.result = None
        self.cancelling = False

    @property
    def options(self):
        return dict(getattr(self.c.entry, "options", {}))

    @property
    def busy(self):
        return self.cancelling or (self.task is not None and not self.task.done())

    @property
    def watching(self):
        return self.watch is not None and time.monotonic() - self.watch["started"] <= 120

    def value(self, entity):
        state = self.c.state(entity)
        return state.state if state else "unavailable"

    def ready(self, check_player=True):
        o = self.options
        required = ("prompt", "record_button", "cancel_button", "record_busy", "record_status", "last_reason")
        if not all(o.get(k) for k in required):
            raise MailboxError("Nejdřív nastav hlasový vzkaz v nastavení integrace Dveřní zvonek P4.")
        if not self.c.door_idle() or self.value(o["record_busy"]) != "off":
            raise MailboxError("P4 musí být bez hovoru a záznamník musí být volný.")
        if check_player and self.value(self.c.config["player"]) not in ("idle", "off"):
            raise MailboxError("Nejdřív zastav přehrávání na P4.")
        for key in ("record_status", "last_reason"):
            if self.value(o[key]) in ("unknown", "unavailable"):
                raise MailboxError("Není dostupná entita " + o[key] + ".")

    def arm(self, context):
        self.disarm()
        if self.options.get("auto_after_timeout", False):
            self.ready(check_player=False)
            self.watch = {"started": time.monotonic(), "at": datetime.now(timezone.utc),
                          "context": context, "rang": False,
                          "phone_entities": {p["state_entity"] for p in self.c.phones()}}

    def disarm(self):
        self.watch = None

    @staticmethod
    def playing(state):
        return state is not None and (state.state in ("playing", "announcing")
                                      or state.attributes.get("announcing") is True)

    def observe(self, entity, old, new):
        o = self.options
        relevant = {self.c.config["door_state"], self.c.config["player"],
                    o.get("record_status"), o.get("record_busy"), o.get("last_reason")}
        if self.watch:
            relevant.update(self.watch["phone_entities"])
        if entity not in relevant:
            return
        if new is None or new.state in ("unknown", "unavailable"):
            self.interrupted = True
            self.disarm()
            return
        if self.busy:
            if entity == self.c.config["door_state"] and new.state != "idle":
                self.interrupted = True
            if entity == self.c.config["player"] and self.playing(new):
                self.play_seen = True
            if entity == o.get("record_status") and self.record_requested:
                if new.state.startswith("Nahravam"):
                    self.record_seen = True
                elif self.record_seen and new.state != "Odesilam do HA":
                    self.result = new.state
                    self.saved = new.state == "Ulozeno v HA"
        if not self.watching:
            self.disarm()
            return
        w = self.watch
        if entity in w["phone_entities"]:
            if new.state == "in_call":
                self.disarm()
                return
            if new.state == "ringing" and new.attributes.get("peer_name") == self.c.config["door_name"]:
                w["rang"] = True
        if entity == self.c.config["door_state"] and new.state == "in_call":
            self.disarm()
            return
        # A previous call's timeout must not trigger recording after cancellation
        # or a network failure. Conservative: missing evidence means no recording.
        if entity in (o.get("last_reason"), self.c.config["door_state"]):
            reason = self.c.state(o["last_reason"])
            if (w["rang"] and self.c.door_idle() and reason and reason.state == "timeout"
                    and reason.last_updated >= w["at"]):
                context = w["context"]
                self.disarm()
                try:
                    self.start(context)
                except MailboxError as exc:
                    self.c.status = "Automatický vzkaz nespuštěn: " + str(exc)

    def start(self, context):
        if self.busy or self.c.lock.locked():
            raise MailboxError("Právě probíhá jiná operace zvonku.")
        self.ready()
        self.disarm()
        self.interrupted = False
        self.play_seen = self.record_seen = self.saved = self.record_requested = False
        self.result = None
        self.phase = "prompt"
        self.c.status = "Přehrávám výzvu k zanechání vzkazu."
        self.task = self.c.hass.async_create_task(self.run(context))

    def guard(self):
        if self.interrupted or not self.c.door_idle():
            raise MailboxError("Sekvence zastavena: hovor nebo nedostupnost P4 má přednost.")

    async def until(self, predicate, seconds):
        async with asyncio.timeout(seconds):
            while True:
                self.guard()
                if predicate():
                    return
                await asyncio.sleep(0.1)

    async def run(self, context):
        o = self.options
        try:
            async with self.c.lock:
                self.ready()
                media = o["prompt"]
                await self.c.service("media_player", "play_media", {
                    "entity_id": self.c.config["player"], "announce": True,
                    "media_content_id": media["media_content_id"],
                    "media_content_type": media["media_content_type"]}, context)
                await self.until(lambda: self.play_seen, 15)
                await self.until(lambda: self.value(self.c.config["player"]) in ("idle", "off")
                                 and not self.playing(self.c.state(self.c.config["player"])), 60)
                await asyncio.sleep(1)
                self.guard()
                if self.value(o["record_busy"]) != "off":
                    raise MailboxError("Záznamník mezitím obsadila jiná operace.")
                self.phase = "recording"
                self.c.status = "Spouštím desetisekundový vzkaz na mikrofonu P4."
                self.record_requested = True
                await self.c.service("button", "press", {"entity_id": o["record_button"]}, context)
                await self.until(lambda: self.record_seen, 8)
                self.c.status = "Nahrávám vzkaz a čekám na potvrzení uložení v HA."
                await self.until(lambda: self.result is not None, 45)
                if not self.saved:
                    raise MailboxError("Uložení nepotvrzeno: " + str(self.result))
                self.c.status = "Vzkaz byl uložen v HA. Najdeš ho v Hlasových vzkazech / Médiích."
        except asyncio.CancelledError:
            self.c.status = "Sekvence vzkazu byla zrušena."
            raise
        except Exception as exc:
            self.c.status = ("Sekvence vzkazu: vypršel čas; uložení není potvrzeno." if isinstance(exc, TimeoutError)
                             else "Sekvence vzkazu: " + (str(exc) or type(exc).__name__)[:800])
        finally:
            self.phase = "idle"

    async def cancel(self, context):
        if self.cancelling:
            return
        self.disarm()
        if not self.busy:
            self.c.status = "Čekání na automatický vzkaz bylo zrušeno."
            return
        phase = self.phase
        self.cancelling = True
        try:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            if phase == "prompt" and self.c.door_idle():
                await self.c.service("media_player", "media_stop", {"entity_id": self.c.config["player"]}, context)
            elif self.record_requested:
                await self.c.service("button", "press", {"entity_id": self.options["cancel_button"]}, context)
                self.c.status = "Zrušení odesláno. Již zahájený upload nelze vzít zpět; ověř Vzkaz stav."
        finally:
            self.phase = "idle"
            self.cancelling = False
