#!/usr/bin/env python3
"""Tests the TI Panel's buttons and menus (knobs are covered by test_wiring.py).

  - every select button (OSC 1-3, LFO 1-3, FILT 1-2, SLOT 1-6, the effect lists) shows its page
  - every parameter toggle (SYNC, HOLD, ENV MODE, KEY TRIG...) flips its parameter when clicked
  - every drop-down menu shows its parameter's value, and follows it when the value changes
Values are put back afterwards.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_skin import attr  # noqa: E402
from mcp import call, find_port  # noqa: E402

port = find_port()
rml = (Path(__file__).parent.parent / "skin" / "TIPanel" / "TIPanel.rml").read_text()
fails = 0


def report(ok, text):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + text)


def element(eid):
    found = json.loads(call(port, "find_elements", {"selector": f"#{eid}"}))
    return next((e for e in found["elements"] if e.get("id") == eid), None)


def param(name):
    return json.loads(call(port, "get_parameter", {"name": name}))


def click(eid):
    call(port, "click_element", {"selector": f"#{eid}"})
    time.sleep(0.3)


# Select buttons: clicking button N of a group must make a control on page N visible.
print("--- select buttons")
groups = {}
for a in re.findall(r'<button([^>]*tabbutton="[^"]*"[^>]*)>', rml):
    g = attr(a, "tabgroup")
    if g and g.startswith("hw"):
        groups.setdefault(g, {})[attr(a, "tabbutton")] = attr(a, "id")
for group, buttons in groups.items():
    for index, bid in sorted(buttons.items()):
        click(bid)
        page_start = rml.index(f'tabgroup="{group}" tabpage="{index}"')
        first = re.compile(r'<(?:knob|combo)[^>]*\bid="(hw[^"]+)"').search(rml, page_start)
        el = element(first.group(1))
        report(bool(el and el["visible"]), f"{bid:14} shows {first.group(1)}")
    click(buttons["0"])

# Parameter toggles.
print("--- toggle buttons")
for a in re.findall(r'<button([^>]*\bparam="[^"]*"[^>]*)>', rml):
    bid, name = attr(a, "id"), attr(a, "param")
    if not (bid or "").startswith("hw"):
        continue
    # Make the toggle's page visible first (e.g. SYNC lives on the OSC 2 page).
    for group, buttons in groups.items():
        for index, sel in buttons.items():
            start = rml.find(f'tabgroup="{group}" tabpage="{index}"')
            end = rml.find("tabpage=", start + 10)
            if start >= 0 and f'id="{bid}"' in rml[start:end if end > 0 else len(rml)]:
                click(sel)
    before = param(name)["value"]
    click(bid)
    after = param(name)["value"]
    call(port, "set_parameter", {"name": name, "value": before})
    report(after != before, f"{bid:14} {name:24} {before} -> {after}")

# Menus: the combo's text must match the parameter, and follow a change.
print("--- drop-down menus")
for a in re.findall(r'<combo([^>]*)>', rml):
    cid, name = attr(a, "id"), attr(a, "param")
    if not (cid or "").startswith("hw"):
        continue
    p = param(name)
    values = p.get("valueList") or []
    if len(values) < 2:
        report(False, f"{cid:14} {name}: no value list")
        continue
    target = p["min"] + 1 if p["value"] == p["min"] else p["min"]
    call(port, "set_parameter", {"name": name, "value": target})
    time.sleep(0.3)
    el = element(cid)
    shown = (el or {}).get("text", "").strip()
    expect = param(name)["text"].strip()
    call(port, "set_parameter", {"name": name, "value": p["value"]})
    report(shown == expect, f"{cid:16} {name:28} shows '{shown}' (expected '{expect}')")

print(f"\n{'ALL GOOD' if not fails else f'{fails} PROBLEMS'}")
