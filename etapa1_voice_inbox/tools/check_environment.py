"""Read-only environment check. Run from the selected test Python environment."""
from importlib.metadata import version, PackageNotFoundError
import sys
import platform

ok = sys.version_info >= (3, 14, 2)
print("Python:", platform.python_version(), "OK" if ok else "NEEDS >=3.14.2")
for name, expected in [("homeassistant", "2026.10.3"), ("aiohttp", "3.14.5"),
                       ("pytest", None), ("pytest-asyncio", None), ("pytest-aiohttp", None)]:
    try:
        installed = version(name)
        matches = expected is None or installed == expected
        print(name, installed, "OK" if matches else f"NEEDS {expected}")
        ok = ok and matches
    except PackageNotFoundError:
        print(name, "MISSING")
        ok = False
if platform.system() != "Linux":
    print("Full HA tests: use Linux/WSL. Standard-library storage tests also run on Windows.")
    ok = False
sys.exit(0 if ok else 1)
