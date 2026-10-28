#!/usr/bin/env python3
"""Drags every knob on the TI Panel and checks the parameter it should control actually moves.

Knobs behind a selector (OSC 1/2/3, LFO 1/2/3, FILT 1/2, SLOT 1-6, the effect lists) are tested
after clicking that selector. Every value is put back afterwards, so the patch is unchanged.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_skin import TAG, attr  # noqa: E402
from mcp import call, find_port  # noqa: E402

port = find_port()
rml = (Path(__file__).parent.parent / "skin" / "TIPanel" / "TIPanel.rml").read_text()

# Walk the markup once: for every hw knob, note the selector page it sits in (if any).
knobs, stack = [], []
for m in TAG.finditer(rml):
    closing, name, attrs, selfclose = m.groups()
    if closing:
        stack.pop()
        continue
    group, page = attr(attrs, "tabgroup"), attr(attrs, "tabpage")
    if name == "knob" and (attr(attrs, "id") or "").startswith("hw"):
        sel = next(((g, p) for g, p in reversed(stack) if g), (None, None))
        knobs.append((attr(attrs, "id"), attr(attrs, "param"), sel))
    if not selfclose:
        stack.append((group, page) if page is not None and group and group.startswith("hw") else (None, None))

buttons = {(attr(a, "tabgroup"), attr(a, "tabbutton")): attr(a, "id")
           for a in re.findall(r'<button([^>]*tabbutton="[^"]*"[^>]*)>', rml)}


def param(name):
    return json.loads(call(port, "get_parameter", {"name": name}))


def box(eid):
    found = json.loads(call(port, "find_elements", {"selector": f"#{eid}"}))
    return next((e.get("box") for e in found["elements"] if e.get("id") == eid and e.get("visible")), None)


failures = 0
for eid, name, (group, page) in knobs:
    if group:
        call(port, "click_element", {"selector": f"#{buttons[(group, page)]}"})
        time.sleep(0.3)
    before = param(name)
    b = box(eid)
    if b is None:
        failures += 1
        print(f"FAIL {eid:20} not visible after clicking its selector")
        continue
    x, y = b["x"] + b["w"] // 2, b["y"] + b["h"] // 2
    up = before["value"] < (before["min"] + before["max"]) / 2
    call(port, "mouse_drag", {"fromX": x, "fromY": y, "toX": x, "toY": y + (-60 if up else 60), "steps": 12})
    time.sleep(0.5)
    after = param(name)
    moved = after["value"] != before["value"]
    call(port, "set_parameter", {"name": name, "value": before["value"]})
    failures += not moved
    where = f"{group}:{page}" if group else "-"
    print(f"{'ok  ' if moved else 'FAIL'} {eid:20} {where:9} {name:42} {before['value']} -> {after['value']}")

print(f"\n{len(knobs) - failures}/{len(knobs)} knobs control their parameter")
