"""Real visitor-button router, simulated state/services, no HA installation."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

path = Path(__file__).parents[1] / "custom_components/p4_doorbell/visitor.py"
spec = importlib.util.spec_from_file_location("visitor_test", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.idle = True
        self.values = {"busy": "off", "status": "Nahravam, nejvyse 10 s"}
        self.mailbox = NS(options={"visitor_sensor": "binary_sensor.bell", "record_busy": "busy",
                                   "record_status": "status", "save_button": "button.save"},
                          phase="idle", busy=False, value=lambda k: self.values.get(k),
                          confirm_recording=lambda: self.calls.append("confirm"))
        async def ring(context):
            self.calls.append("ring")
        async def service(domain, action, data, context):
            self.calls.append((domain, action, data))
        self.c = NS(mailbox=self.mailbox, lock=asyncio.Lock(), status="", ring=ring,
                    service=service, door_idle=lambda: self.idle, hass=NS(async_create_task=asyncio.create_task))
        self.v = mod.VisitorButton(self.c)

    async def test_idle_press_rings_once(self):
        await self.v.press(None)
        await self.v.press(None)
        self.assertEqual(self.calls, ["ring"])

    async def test_waiting_press_confirms(self):
        self.mailbox.phase = "waiting_button"
        self.mailbox.busy = True
        await self.v.press(None)
        self.assertEqual(self.calls, ["confirm"])

    async def test_recording_press_saves_not_rings(self):
        self.mailbox.phase = "recording"
        self.mailbox.busy = True
        await self.v.press(None)
        self.assertEqual(self.calls, [("button", "press", {"entity_id": "button.save"})])
        self.assertEqual(self.mailbox.phase, "uploading")

    async def test_prompt_upload_and_active_call_ignore(self):
        for phase in ("prompt", "uploading"):
            self.mailbox.phase = phase
            self.mailbox.busy = True
            self.v.last_press = -float("inf")
            await self.v.press(None)
        self.mailbox.busy = False
        self.idle = False
        self.v.last_press = -float("inf")
        await self.v.press(None)
        self.assertFalse(self.calls)

    async def test_reconnect_and_startup_do_not_ring(self):
        for old in (None, NS(state="unavailable"), NS(state="unknown"), NS(state="on")):
            self.v.observe("binary_sensor.bell", old, NS(state="on"), None)
        self.assertIsNone(self.v.task)

    async def test_only_selected_off_to_on_edge(self):
        self.v.observe("binary_sensor.other", NS(state="off"), NS(state="on"), None)
        self.assertIsNone(self.v.task)
        self.v.observe("binary_sensor.bell", NS(state="off"), NS(state="on"), None)
        await self.v.task
        self.assertEqual(self.calls, ["ring"])

    async def test_external_recording_not_interrupted(self):
        self.values["busy"] = "on"
        await self.v.press(None)
        self.assertFalse(self.calls)

    async def test_no_save_until_microphone_reports_recording(self):
        self.mailbox.phase = "recording"
        self.mailbox.busy = True
        self.values["status"] = "Pripraveno"
        await self.v.press(None)
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
