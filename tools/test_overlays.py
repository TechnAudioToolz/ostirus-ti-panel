#!/usr/bin/env python3
"""Open every pop-up (BROWSE, the EDIT buttons, COMMON, PARTS) and close it again."""
import json, sys, time
sys.path.insert(0, "tools")
from mcp import call, find_port

port = find_port()

def visible(eid):
    found = json.loads(call(port, "find_elements", {"selector": f"#{eid}"}))
    return next((e["visible"] for e in found["elements"] if e.get("id") == eid), None)

ok = True
for opener, ovl in [("hwBrowse", 1), ("hwOscEdit", 2), ("hwFiltEdit", 3), ("hwLfoEdit", 4), ("hwMatEdit", 5),
                    ("hwArpEdit", 6), ("hwFxBEdit", 7), ("hwFxAEdit", 8), ("hwCommon", 9), ("hwParts", 10)]:
    call(port, "click_element", {"selector": f"#{opener}"}); time.sleep(0.3)
    opened = visible(f"hwOvl{ovl}")
    call(port, "click_element", {"selector": f"#hwOvl{ovl}Close"}); time.sleep(0.3)
    closed = not visible(f"hwOvl{ovl}")
    ok &= bool(opened and closed)
    print(f"{opener:11} opens: {opened!s:5}  CLOSE closes: {closed}")
print("ALL GOOD" if ok else "PROBLEMS FOUND")
