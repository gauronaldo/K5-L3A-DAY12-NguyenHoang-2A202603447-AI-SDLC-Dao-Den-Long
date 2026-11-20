#!/usr/bin/env python3
"""Zip the build_apps output into dist/ with executable bits preserved (works when building on Windows).

    python setup.py build_apps && python3 tools/package_release.py
"""
import os
import stat
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.0.0"
TARGETS = {"win_amd64": "windows-x64", "manylinux2014_x86_64": "linux-x64", "macosx_10_9_x86_64": "macos-x64"}
EXEC_NAMES = {"DaoDenLong", "DaoDenLong-headless", "DaoDenLong-soak"}


def is_exec(platform, rel):
    name = os.path.basename(rel)
    if platform == "win_amd64":
        return False
    return name in EXEC_NAMES or "/Contents/MacOS/" in "/" + rel.replace(os.sep, "/") and "." not in name


def main():
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    for plat, label in TARGETS.items():
        src = os.path.join(ROOT, "build", plat)
        if not os.path.isdir(src):
            print("skip", plat)
            continue
        top = "DaoDenLong-%s-%s" % (VERSION, label)
        out = os.path.join(ROOT, "dist", top + ".zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, _, files in os.walk(src):
                for f in sorted(files):
                    full = os.path.join(dirpath, f)
                    rel = os.path.relpath(full, src)
                    info = zipfile.ZipInfo.from_file(full, os.path.join(top, rel).replace(os.sep, "/"))
                    mode = 0o755 if is_exec(plat, rel) else 0o644
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(full, "rb") as fh:
                        z.writestr(info, fh.read())
            z.writestr(top + "/README.txt", README.format(label=label))
        print("wrote", os.path.relpath(out, ROOT), "%.1f MB" % (os.path.getsize(out) / 1048576))


README = """Dao Den Long v1.0.0 ({label})

Windows : DaoDenLong.exe                     (game)
Linux   : ./DaoDenLong                       (game; needs an OpenGL driver)
macOS   : open DaoDenLong.app  or ./DaoDenLong   (x86_64; Apple Silicon runs it through Rosetta 2.
          First launch: right-click > Open, because the app is not signed.)

Headless (Test Contract v1.3):  DaoDenLong-headless --seed 1 --night 1 --ticks 600 --out out.jsonl
Soak test:                      DaoDenLong-soak --seed 7 --nights 10 --out soak.json
Benchmark:                      DaoDenLong --bench --seed 42 --duration 30 --out bench.json

Source, tests and evidence: https://github.com/gauronaldo/K5-L3A-DAY12-NguyenHoang-2A202603447-AI-SDLC-Dao-Den-Long
"""

if __name__ == "__main__":
    main()
