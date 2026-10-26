"""Small doorbell controller using public VoIP services and entity states.

Does not import or fork VoIP internals. Version-specific entity discovery is
explicit and fails closed when the expected public entities are unavailable.
"""
import asyncio
import time
import uuid
from homeassistant.helpers import entity_registry as er, device_registry as dr


class DoorbellError(Exception):
    pass


def groups(value):
    return [part.strip() for part in value.split(",") if part.strip()]


class Controller:
    def __init__(self, hass, entry):
        self.hass, self.entry = hass, entry
        self.config = entry.data
        self.group = "P4-dvere-" + entry.entry_id[:8]
        self.lock = asyncio.Lock()
        self.visit = ""
        self.started = 0.0
        self.status = "Připraveno — nejdřív zkontroluj a zapoj panely."

    def state(self, entity):
        return self.hass.states.get(entity)

    def door_idle(self):
        state = self.state(self.config["door_state"])
        return state is not None and state.state.lower() == "idle"

    def phones(self):
        registry, devices = er.async_get(self.hass), dr.async_get(self.hass)
        result = []
        for device_id in self.config["receivers"]:
            device = devices.async_get(device_id)
            entities = [e for e in er.async_entries_for_device(registry, device_id)
                        if e.platform == "voip_stack" and not e.disabled_by]
            def find(domain, suffix):
                matches = [e.entity_id for e in entities if e.domain == domain and e.unique_id.endswith(suffix)]
                if len(matches) != 1:
                    raise DoorbellError("U přijímače chybí jednoznačná entita " + suffix + ". Ověř verzi VoIP Stacku.")
                return matches[0]
            item = {"device_id": device_id,
                    "name": (device.name_by_user or device.name) if device else device_id,
                    "state_entity": find("sensor", "_call_state"),
                    "group_entity": find("text", "_ring_group"),
                    "auto_entity": find("switch", "_auto_answer")}
            state = self.state(item["state_entity"])
            if not state or state.attributes.get("endpoint_kind") != "browser":
                raise DoorbellError("První verze podporuje přijímací telefony HA v prohlížeči, ne ESP/SIP účty.")
            group_state = self.state(item["group_entity"])
            if not group_state or group_state.state in ("unavailable", "unknown"):
                raise DoorbellError("Není dostupné nastavení skupiny přijímače.")
            item.update(state=state.state, call_id=state.attributes.get("call_id", ""),
                        peer=state.attributes.get("peer_name", ""),
                        direction=state.attributes.get("direction", ""),
                        groups=groups(group_state.state))
            result.append(item)
        return result

    async def service(self, domain, name, data, context):
        if not self.hass.services.has_service(domain, name):
            raise DoorbellError(f"Chybí akce {domain}.{name}; ověř nainstalovaný VoIP Stack.")
        await self.hass.services.async_call(domain, name, data, blocking=True, context=context)

    async def wait_for(self, predicate, seconds=8):
        async with asyncio.timeout(seconds):
            while not predicate():
                await asyncio.sleep(0.1)

    def snapshot(self):
        issues = []
        try:
            phones = self.phones()
        except DoorbellError as exc:
            phones = []
            issues.append(str(exc))
        for phone in phones:
            if self.group not in phone["groups"]:
                issues.append(f'{phone["name"]}: zatím není ve zvonkové skupině.')
            auto = self.state(phone["auto_entity"])
            if not auto or auto.state != "off":
                issues.append(f'{phone["name"]}: vypni automatický příjem ve VoIP.')
        door = self.state(self.config["door_state"])
        return {"group": self.group, "phones": phones, "issues": issues,
                "camera": self.config["camera"], "door_state": door.state if door else "unavailable",
                "status": self.status, "visit": self.visit, "busy": self.lock.locked(),
                "reply_label": self.config["reply_label"]}

    async def enroll(self, context):
        async with self.lock:
            if not self.door_idle():
                raise DoorbellError("P4 musí být v klidu (VoIP State: idle).")
            for phone in self.phones():
                current = phone["groups"]
                if self.group not in current:
                    value = ", ".join([*current, self.group])
                    if len(value) > 255:
                        raise DoorbellError("Seznam skupin přijímače by překročil povolenou délku.")
                    await self.service("text", "set_value", {"entity_id": phone["group_entity"], "value": value}, context)
            self.status = "Panely zapojeny. Původní skupiny zůstaly zachované."

    async def ring(self, context):
        # Refuse, rather than queue, double presses from different displays.
        if self.lock.locked():
            raise DoorbellError("Probíhá jiná operace zvonku.")
        async with self.lock:
            if not self.door_idle() or time.monotonic() - self.started < 5:
                raise DoorbellError("P4 právě volá nebo ještě běží ochrana proti dvojstisku.")
            issues = self.snapshot()["issues"]
            if issues:
                raise DoorbellError(" ".join(issues))
            self.visit = uuid.uuid4().hex
            self.started = time.monotonic()
            self.status = "Vyzváním na vybraných panelech."
            try:
                await self.service("voip_stack", "call", {
                    "device_id": self.config["door_device"], "destination": self.group,
                    "ha_bridge": True, "send_video": False}, context)
            except BaseException:
                self.visit = ""
                self.status = "Zahájení hovoru nebylo potvrzeno; ověř stav P4."
                raise

    async def reply(self, device_id, visit, call_id, context):
        if self.lock.locked():
            raise DoorbellError("Probíhá jiná operace zvonku.")
        async with self.lock:
            if not visit or visit != self.visit or time.monotonic() - self.started > 90:
                raise DoorbellError("Tato návštěva již není aktuální. Znovu zazvoň testovacím tlačítkem.")
            phone = next((p for p in self.phones() if p["device_id"] == device_id), None)
            if (not phone or phone["state"] != "ringing" or not call_id or phone["call_id"] != call_id
                    or phone["direction"] != "incoming" or phone["peer"] != self.config["door_name"]):
                raise DoorbellError("Na tomto panelu již nevyzvání odpovídající hovor od P4. Ověř také název volajícího.")
            self.status = "Přebírám vyzvánění pro přednastavenou odpověď."
            # VoIP's transactional answer chooses the sole winner. Do NOT hang up
            # P4 blindly: another receiver may have won between our check and answer.
            scope = {"device_id": device_id, "call_id": call_id}
            await self.service("voip_stack", "answer", {
                **scope, "send_video": False, "media_client_id": "doorbell-reply-" + uuid.uuid4().hex}, context)
            def won():
                state = self.state(phone["state_entity"])
                return state and state.state == "in_call" and state.attributes.get("call_id") == call_id
            try:
                await self.wait_for(won)
            except TimeoutError:
                self.status = "Převzetí nebylo potvrzené. Odpověď se nepřehrála; ověř telefonní kartu."
                raise DoorbellError(self.status) from None
            # Only the confirmed answering receiver's exact call is ended.
            await self.service("voip_stack", "hangup", scope, context)
            try:
                await self.wait_for(self.door_idle)
            except TimeoutError:
                raise DoorbellError("P4 se po zavěšení neuvolnila. Odpověď se nepřehrála.") from None
            self.visit = ""
            media = self.config["reply"]
            await self.service("media_player", "play_media", {
                "entity_id": self.config["player"],
                "media_content_id": media["media_content_id"],
                "media_content_type": media["media_content_type"], "announce": True}, context)
            self.status = "Odpověď odeslána do přehrávače P4; poslechem ověř přehrání."
