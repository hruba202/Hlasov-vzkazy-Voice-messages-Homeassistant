"""Regression of actual lifecycle functions against yielding HA test doubles.

Uses stdlib only. AST loading avoids importing/installing HA on Windows. This
checks orchestration, not HA middleware, platforms or an actual HA startup.
"""
import ast
import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/voice_inbox"


def load_definitions(filename, names, namespace):
    tree = ast.parse((COMPONENT / filename).read_text(encoding="utf-8-sig"))
    selected = [node for node in tree.body if getattr(node, "name", None) in names]
    assert len(selected) == len(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(COMPONENT / filename), "exec"), namespace)


class NotReady(Exception):
    pass


class Store:
    def __init__(self, *args):
        self.broken = False

    def snapshot(self):
        if self.broken:
            raise OSError("storage unavailable")
        return {"count": 0, "latest": {}}


class CoordinatorBase:
    def __init__(self, hass, logger, *, config_entry="implicit-entry", **kwargs):
        # Old code inherited the entry from HA's ContextVar.
        self.config_entry = config_entry
        self.hass = hass
        self.last_update_success = True
        self.data = None
        self.shutdown_calls = 0

    async def async_register_shutdown(self):
        assert self.config_entry is None, "global coordinator belongs to first source"
        await asyncio.sleep(0)
        self.shutdown_calls += 1

    async def async_refresh(self):
        await asyncio.sleep(0)
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except RuntimeError:
            self.last_update_success = False

    async def async_config_entry_first_refresh(self):
        raise AssertionError("entry-only first_refresh used on shared coordinator")


class HTTP:
    def __init__(self):
        self.views = set()
        self.static = set()
        self.static_calls = 0
        self.fail_static_once = False

    def register_view(self, view):
        name = type(view).__name__
        assert name not in self.views, "duplicate HTTP view"
        self.views.add(name)

    async def async_register_static_paths(self, configs):
        await asyncio.sleep(0)  # Reproduces overlapping startup entries.
        if self.fail_static_once:
            self.fail_static_once = False
            raise RuntimeError("static preparation failed")
        for config in configs:
            assert config[0] not in self.static, "duplicate static GET route"
            self.static.add(config[0])
        self.static_calls += 1


class Entries:
    def __init__(self):
        self.loaded = set()
        self.fail_once = False
        self.refuse_unload = False

    async def async_forward_entry_setups(self, entry, platforms):
        await asyncio.sleep(0)
        self.loaded.add(entry.data["source"])
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("platform failure")

    async def async_unload_platforms(self, entry, platforms):
        await asyncio.sleep(0)
        if self.refuse_unload:
            return False
        self.loaded.discard(entry.data["source"])
        return True


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.panels = set()
        self.panel_calls = 0

        async def register_panel(hass, frontend_url_path, **kwargs):
            await asyncio.sleep(0)
            assert frontend_url_path not in self.panels, "duplicate panel"
            self.panels.add(frontend_url_path)
            self.panel_calls += 1

        async def executor(fn, *args):
            await asyncio.sleep(0)
            return fn(*args)

        self.hass = SimpleNamespace(data={}, config=SimpleNamespace(media_dirs={}),
                                    http=HTTP(), config_entries=Entries(),
                                    async_add_executor_job=executor)
        self.ns = dict(asyncio=asyncio, Store=Store, Attempts=lambda: None,
                       DOMAIN="voice_inbox", PANEL="voice-inbox", MAX_FILES=100,
                       PLATFORMS=["sensor", "binary_sensor"], Path=Path,
                       __file__=str(COMPONENT / "browser.py"),
                       LOGGER=logging.getLogger(__name__), timedelta=timedelta,
                       DataUpdateCoordinator=CoordinatorBase, UpdateFailed=RuntimeError,
                       ConfigEntryNotReady=NotReady,
                       select_media_directory=lambda dirs: ("local", Path("/media")),
                       StaticPathConfig=lambda *args: args,
                       frontend=SimpleNamespace(
                           async_panel_exists=lambda hass, panel: panel in self.panels,
                           async_remove_panel=lambda hass, panel: self.panels.discard(panel)),
                       panel_custom=SimpleNamespace(async_register_panel=register_panel))
        for name in ("UploadView", "BrowserUploadView", "BrowserStateView", "BrowserAudioView"):
            self.ns[name] = type(name, (), {"__init__": lambda self, *args: None})
        load_definitions("http.py", {"Runtime"}, self.ns)
        load_definitions("coordinator.py", {"InboxCoordinator"}, self.ns)
        load_definitions("browser.py", {"async_register_browser"}, self.ns)
        load_definitions("__init__.py", {"async_setup_entry", "async_unload_entry"}, self.ns)
        self.entries = [SimpleNamespace(data={"source": name}) for name in ("annahp", "panel7", "p4")]

    async def setup_entry(self, entry):
        return await self.ns["async_setup_entry"](self.hass, entry)

    async def unload(self, entry):
        return await self.ns["async_unload_entry"](self.hass, entry)

    @property
    def runtime(self):
        return self.hass.data["voice_inbox"]

    async def test_three_concurrent_sources(self):
        self.assertEqual(await asyncio.gather(*(self.setup_entry(e) for e in self.entries)), [True]*3)
        self.assertEqual(set(self.runtime.sources), {"annahp", "panel7", "p4"})
        self.assertEqual(self.hass.http.static_calls, 1)
        self.assertEqual(len(self.hass.http.views), 4)
        self.assertEqual(self.panel_calls, 1)
        self.assertIsNone(self.runtime.coordinator.config_entry)
        self.assertEqual(self.runtime.coordinator.shutdown_calls, 1)

    async def test_sequential_add_and_reload_first_source(self):
        for entry in self.entries:
            await self.setup_entry(entry)
        coordinator = self.runtime.coordinator
        self.assertTrue(await self.unload(self.entries[0]))
        self.assertIn("voice-inbox", self.panels)
        self.assertEqual(set(self.runtime.sources), {"panel7", "p4"})
        self.assertTrue(await self.setup_entry(self.entries[0]))
        self.assertIs(coordinator, self.runtime.coordinator)
        self.assertEqual(self.hass.http.static_calls, 1)

    async def test_unload_all_then_setup_again(self):
        for entry in self.entries:
            await self.setup_entry(entry)
        for entry in self.entries:
            self.assertTrue(await self.unload(entry))
        self.assertFalse(self.panels)
        await self.setup_entry(self.entries[2])
        self.assertEqual(self.panel_calls, 2)
        self.assertEqual(self.hass.http.static_calls, 1)
        self.assertEqual(self.runtime.coordinator.shutdown_calls, 1)

    async def test_browser_registration_is_concurrency_safe_independently(self):
        runtime = self.ns["Runtime"]()
        await asyncio.gather(*(self.ns["async_register_browser"](self.hass, runtime) for _ in range(3)))
        self.assertEqual(self.hass.http.static_calls, 1)
        self.assertEqual(self.panel_calls, 1)

    async def test_static_failure_retry_does_not_repeat_views(self):
        self.hass.http.fail_static_once = True
        with self.assertRaises(RuntimeError):
            await self.setup_entry(self.entries[0])
        self.assertFalse(self.runtime.sources)
        await self.setup_entry(self.entries[0])
        self.assertEqual(len(self.hass.http.views), 4)
        self.assertEqual(self.hass.http.static_calls, 1)

    async def test_platform_failure_rolls_back_source_and_retries(self):
        self.hass.config_entries.fail_once = True
        with self.assertRaises(RuntimeError):
            await self.setup_entry(self.entries[0])
        self.assertFalse(self.runtime.sources)
        self.assertFalse(self.hass.config_entries.loaded)
        await self.setup_entry(self.entries[0])
        self.assertEqual(self.hass.http.static_calls, 1)

    async def test_busy_and_failed_unload_keep_source(self):
        await self.setup_entry(self.entries[0])
        self.runtime.active.add("annahp")
        self.assertFalse(await self.unload(self.entries[0]))
        self.runtime.active.clear()
        self.hass.config_entries.refuse_unload = True
        self.assertFalse(await self.unload(self.entries[0]))
        self.assertIn("annahp", self.runtime.sources)

    async def test_inventory_failure_retries_without_losing_other_source(self):
        await self.setup_entry(self.entries[0])
        self.runtime.store.broken = True
        with self.assertRaises(NotReady):
            await self.setup_entry(self.entries[1])
        self.assertEqual(set(self.runtime.sources), {"annahp"})
        self.runtime.store.broken = False
        await self.setup_entry(self.entries[1])
        self.assertEqual(set(self.runtime.sources), {"annahp", "panel7"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
