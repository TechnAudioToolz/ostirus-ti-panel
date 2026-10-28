#!/usr/bin/env python3
"""Downloads OsTIrus's TrancyTI skin (GPL-3.0, from gearmulator) into reference/TrancyTI.

The TI Panel is built from these files; they aren't kept in this repo.
"""
import json
import sys
import urllib.request
from pathlib import Path

TAG = "2.2.27"
REPO = "dsp56300/gearmulator"
PATH = "source/axel/osTIrusJucePlugin/skins/TrancyTI"
DEST = Path(__file__).resolve().parent.parent / "reference" / "TrancyTI"


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


listing = json.loads(get(f"https://api.github.com/repos/{REPO}/contents/{PATH}?ref={TAG}"))
files = [f["name"] for f in listing if f["type"] == "file"]
DEST.mkdir(parents=True, exist_ok=True)
for i, name in enumerate(files, 1):
    (DEST / name).write_bytes(get(f"https://raw.githubusercontent.com/{REPO}/{TAG}/{PATH}/{name}"))
    print(f"\r{i}/{len(files)} {name:60}", end="", file=sys.stderr)
print(f"\nfetched {len(files)} files into {DEST}")
