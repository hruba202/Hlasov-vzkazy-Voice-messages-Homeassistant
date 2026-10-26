"""Exercise real HTTP view exception handling without installing HA."""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

class HAError(Exception):
    translation_key = "esphome_action_missing"

class BaseView:
    def context(self, request):
        return None

source = Path(__file__).parents[1] / "custom_components/p4_doorbell/__init__.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "View"]
scope = dict(HomeAssistantView=BaseView, HomeAssistantError=HAError,
             MailboxError=type("MailboxError", (Exception,), {}),
             DoorbellError=type("DoorbellError", (Exception,), {}),
             LOGGER=logging.getLogger("test"),
             web=NS(json_response=lambda data, status=200, **kwargs: (status, data)))
exec(compile(tree, str(source), "exec"), scope)

class Tests(unittest.IsolatedAsyncioTestCase):
    async def check_error(self, error):
        async def ring(context):
            raise error
        controller = NS(ring=ring, status="")
        view = scope["View"](None, {"controller": controller})
        class Request(dict):
            content_length = 17
            async def json(self):
                return {"action": "ring"}
        return await view.post(Request(hass_user=NS(is_admin=True)))

    async def test_actual_reason_and_translation_key_survive(self):
        status, data = await self.check_error(HAError("Missing start_call action"))
        self.assertEqual(status, 503)
        self.assertIn("Missing start_call action", data["error"])
        self.assertIn("esphome_action_missing", data["error"])

    async def test_timeout_has_distinct_message(self):
        status, data = await self.check_error(TimeoutError())
        self.assertEqual(status, 503)
        self.assertIn("Vypršel čas", data["error"])

if __name__ == "__main__":
    unittest.main()
