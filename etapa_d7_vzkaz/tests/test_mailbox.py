"""Real mailbox state machine; simulated HA events, no external packages."""
import asyncio
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

path = Path(__file__).parents[1] / "custom_components/p4_doorbell/mailbox.py"
spec = importlib.util.spec_from_file_location("mailbox_under_test", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Mailbox, MailboxError = module.Mailbox, module.MailboxError


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.options = dict(auto_after_timeout=True, prompt={"media_content_id": "media-source://media_source/local/prompt.wav",
                            "media_content_type": "audio/wav"}, record_button="button.record",
                            cancel_button="button.cancel", record_busy="binary_sensor.busy",
                            record_status="sensor.record", last_reason="sensor.reason")
        self.states = {}
        for entity, value in (("sensor.door", "idle"), ("media_player.door", "idle"),
                              ("binary_sensor.busy", "off"), ("sensor.record", "Ulozeno v HA"),
                              ("sensor.reason", "timeout")):
            self.states[entity] = NS(state=value, attributes={}, last_updated=datetime.now(timezone.utc)-timedelta(minutes=1))
        self.calls = []
        self.record_result = "Ulozeno v HA"
        self.c = NS(entry=NS(options=self.options), config=dict(door_state="sensor.door", player="media_player.door", door_name="ESP32-P4"),
                    state=self.states.get, lock=asyncio.Lock(), status="", hass=NS(async_create_task=asyncio.create_task))
        self.c.door_idle = lambda: self.states["sensor.door"].state == "idle"
        self.c.phones = lambda: [dict(state_entity="sensor.phone")]
        self.m = Mailbox(self.c)
        async def service(domain, action, data, context):
            self.calls.append((domain, action, data))
            if action == "play_media":
                self.emit("media_player.door", "playing")
                asyncio.get_running_loop().call_soon(self.emit, "media_player.door", "idle")
            if action == "press" and data["entity_id"] == "button.record":
                self.emit("sensor.record", "Nahravam, nejvyse 10 s")
                self.emit("sensor.record", "Odesilam do HA")
                self.emit("sensor.record", self.record_result)
        self.c.service = service

    def emit(self, entity, value, **attrs):
        old = self.states.get(entity)
        new = NS(state=value, attributes=attrs, last_updated=datetime.now(timezone.utc))
        self.states[entity] = new
        self.m.observe(entity, old, new)

    def ringing(self):
        self.m.arm("user-context")
        self.emit("sensor.door", "calling")
        self.emit("sensor.reason", "")
        self.emit("sensor.phone", "ringing", peer_name="ESP32-P4")

    async def test_full_sequence_success(self):
        self.m.start("context")
        await self.m.task
        self.assertEqual([c[1] for c in self.calls], ["play_media", "press"])
        self.assertTrue(self.m.saved)
        self.assertIn("byl uložen", self.c.status)

    async def test_upload_failure_not_reported_as_saved(self):
        self.record_result = "HTTP 507: plna schranka nebo disk HA"
        self.m.start(None)
        await self.m.task
        self.assertFalse(self.m.saved)
        self.assertIn("507", self.c.status)

    async def test_fresh_timeout_after_ringing_starts_once(self):
        self.m.start = Mock()
        self.ringing()
        self.emit("sensor.reason", "timeout")
        self.emit("sensor.door", "idle")
        self.emit("sensor.reason", "timeout")
        self.m.start.assert_called_once_with("user-context")

    async def test_answer_prevents_voicemail(self):
        self.m.start = Mock()
        self.ringing()
        self.emit("sensor.phone", "in_call")
        self.emit("sensor.reason", "timeout")
        self.emit("sensor.door", "idle")
        self.m.start.assert_not_called()

    async def test_stale_timeout_rejected(self):
        self.m.start = Mock()
        self.m.arm(None)
        self.emit("sensor.door", "calling")
        self.emit("sensor.phone", "ringing", peer_name="ESP32-P4")
        self.emit("sensor.door", "idle")
        self.m.start.assert_not_called()

    async def test_cancelled_or_failed_call_not_timeout(self):
        self.m.start = Mock()
        for reason in ("local_hangup", "remote_hangup", "declined", "transport_error"):
            self.ringing()
            self.emit("sensor.reason", reason)
            self.emit("sensor.door", "idle")
        self.m.start.assert_not_called()

    async def test_no_ringing_no_recording(self):
        self.m.start = Mock()
        self.m.arm(None)
        self.emit("sensor.reason", "timeout")
        self.m.start.assert_not_called()

    async def test_offline_invalidates_attempt(self):
        self.m.start = Mock()
        self.ringing()
        self.emit("sensor.door", "unavailable")
        self.emit("sensor.reason", "timeout")
        self.emit("sensor.door", "idle")
        self.m.start.assert_not_called()

    async def test_unrelated_state_removal_does_not_interrupt(self):
        self.ringing()
        self.m.observe("light.kitchen", None, None)
        self.assertTrue(self.m.watching)

    async def test_automatic_disabled_by_default(self):
        self.options.pop("auto_after_timeout")
        self.m.arm(None)
        self.assertFalse(self.m.watching)

    async def test_busy_recorder_and_call_refused(self):
        self.emit("binary_sensor.busy", "on")
        with self.assertRaises(MailboxError):
            self.m.start(None)
        self.emit("binary_sensor.busy", "off")
        self.emit("sensor.door", "in_call")
        with self.assertRaises(MailboxError):
            self.m.start(None)
        self.assertFalse(self.calls)

    async def test_double_start_refused(self):
        self.m.start(None)
        with self.assertRaises(MailboxError):
            self.m.start(None)
        await self.m.cancel(None)
        self.assertFalse(self.m.busy)
        self.assertEqual(self.m.phase, "idle")

    async def test_new_call_during_prompt_never_records(self):
        original = self.c.service
        async def service(*args):
            await original(*args)
            self.emit("sensor.door", "in_call")
        self.c.service = service
        self.m.start(None)
        await self.m.task
        self.assertFalse(any(c[1] == "press" for c in self.calls))

    async def test_missing_playback_confirmation_never_records(self):
        async def fail_wait(predicate, seconds):
            raise TimeoutError()
        self.m.until = fail_wait
        self.m.start(None)
        await self.m.task
        self.assertFalse(any(c[1] == "press" for c in self.calls))
        self.assertFalse(self.m.saved)


if __name__ == "__main__":
    unittest.main()
