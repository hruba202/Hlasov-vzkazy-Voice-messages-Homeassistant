"""Tests of real controller logic with simulated HA; no HA installation needed."""
import asyncio
import ast
from pathlib import Path
import time
from types import SimpleNamespace as NS
import unittest

SOURCE = Path(__file__).parents[1] / "custom_components/p4_doorbell/controller.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module.startswith("homeassistant"))]
namespace = {}
exec(compile(tree, str(SOURCE), "exec"), namespace)
Controller, Error = namespace["Controller"], namespace["DoorbellError"]


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.states = {"door": NS(state="idle"), "auto": NS(state="off")}
        config = dict(door_state="door", door_device="p4", door_name="ESP32-P4",
                      camera="camera.p4", player="media_player.p4", reply_label="Odpověď",
                      receivers=["panel"], reply=dict(media_content_id="media-source://media_source/local/reply.wav", media_content_type="audio/wav"))
        self.c = Controller(NS(states=NS(get=self.states.get)), NS(data=config, entry_id="12345678"))
        self.phone = dict(device_id="panel", name="Panel", state="ringing", call_id="call-1",
                          direction="incoming", peer="ESP32-P4", groups=[self.c.group],
                          auto_entity="auto", state_entity="phone", group_entity="group")
        self.c.phones = lambda: [self.phone]
        self.c.visit = "visit"
        self.c.started = time.monotonic() - 6
        self.calls = []
        self.answer_error = False
        self.stuck = False
        async def service(domain, name, data, context):
            self.calls.append((domain, name, data))
            if name == "answer":
                if self.answer_error:
                    raise Error("Jiný panel vyhrál")
                self.states["phone"] = NS(state="in_call", attributes={"call_id": "call-1"})
                self.states["door"] = NS(state="in_call")
            if name == "hangup" and not self.stuck:
                self.states["door"] = NS(state="idle")
            if name == "set_value":
                self.phone["groups"] = namespace["groups"](data["value"])
        self.c.service = service
        async def wait(predicate, seconds=8):
            if not predicate():
                raise TimeoutError()
        self.c.wait_for = wait

    async def test_enroll_preserves_groups_and_is_idempotent(self):
        self.phone["groups"] = ["Rodina", "Test"]
        await self.c.enroll(None)
        await self.c.enroll(None)
        self.assertEqual(self.phone["groups"], ["Rodina", "Test", self.c.group])
        self.assertEqual(len(self.calls), 1)

    async def test_ring_and_double_press(self):
        await self.c.ring(None)
        self.assertEqual(self.calls[0][2]["destination"], self.c.group)
        with self.assertRaises(Error):
            await self.c.ring(None)
        self.assertEqual(len(self.calls), 1)

    async def test_auto_answer_blocks_ring(self):
        self.states["auto"].state = "on"
        with self.assertRaises(Error):
            await self.c.ring(None)
        self.assertFalse(self.calls)

    async def test_unenrolled_blocks_ring(self):
        self.phone["groups"] = []
        with self.assertRaises(Error):
            await self.c.ring(None)
        self.assertFalse(self.calls)

    async def test_reply_winner_exact_hangup_then_media(self):
        await self.c.reply("panel", "visit", "call-1", None)
        self.assertEqual([c[1] for c in self.calls], ["answer", "hangup", "play_media"])
        self.assertEqual(self.calls[1][2], {"device_id": "panel", "call_id": "call-1"})
        self.assertEqual(self.calls[2][2]["entity_id"], "media_player.p4")
        self.assertEqual(self.c.visit, "")

    async def test_lost_race_never_hangs_up_or_plays(self):
        self.answer_error = True
        with self.assertRaises(Error):
            await self.c.reply("panel", "visit", "call-1", None)
        self.assertEqual([c[1] for c in self.calls], ["answer"])

    async def test_stale_or_foreign_reply_rejected(self):
        for args in [("other", "visit", "call-1"), ("panel", "old", "call-1"), ("panel", "visit", "other")]:
            with self.assertRaises(Error):
                await self.c.reply(*args, None)
        self.assertFalse(self.calls)

    async def test_busy_door_after_hangup_no_play(self):
        self.stuck = True
        with self.assertRaises(Error):
            await self.c.reply("panel", "visit", "call-1", None)
        self.assertEqual([c[1] for c in self.calls], ["answer", "hangup"])

    async def test_concurrent_operation_rejected(self):
        async with self.c.lock:
            with self.assertRaises(Error):
                await self.c.reply("panel", "visit", "call-1", None)
        self.assertFalse(self.calls)

    async def test_wrong_caller_no_side_effects(self):
        self.phone["peer"] = "Jiný telefon"
        with self.assertRaises(Error):
            await self.c.reply("panel", "visit", "call-1", None)
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
