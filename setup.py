"""Release build with Panda3D's build_apps: python setup.py build_apps  (see docs/release.md)."""
from setuptools import setup

setup(
    name="DaoDenLong",
    version="1.0.0",
    options={
        "build_apps": {
            "gui_apps": {"DaoDenLong": "main.py"},
            "console_apps": {"DaoDenLong-headless": "headless.py", "DaoDenLong-soak": "soak.py"},
            "include_patterns": ["assets/sounds/*.wav", "game.contract.json", "LICENSE", "CREDITS.md"],
            "plugins": ["pandagl", "p3openal_audio"],
            "platforms": ["win_amd64"],   # release targets Windows; macOS/Linux run from source (README)
            "include_modules": ["lantern.*"],
            "use_optimized_wheels": False,   # plain PyPI wheels (the optimised ones download from a slow mirror)
        }
    },
)
