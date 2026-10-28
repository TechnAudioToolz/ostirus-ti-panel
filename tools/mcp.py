#!/usr/bin/env python3
"""Talk to a running OsTIrus through gearmulator's built-in MCP server.

Enable it once in OsTIrus: Settings -> Skins -> Developer Options -> Enable MCP Server.

Usage:
    tools/mcp.py health                      # is OsTIrus reachable?
    tools/mcp.py tools                       # list the server's tools
    tools/mcp.py call <tool> ['<json args>'] # call any tool, print its result
    tools/mcp.py reload                      # press F5 (reload the skin), then report error dialogs
    tools/mcp.py shot [out.png]              # screenshot of the editor, copied to out.png
"""
import json
import os
import shutil
import sys
import urllib.request

DISCOVERY = os.path.expanduser("~/.gearmulator_mcp.json")


def find_port():
    """Port of the running OsTIrus instance, from the discovery file (default 13710)."""
    try:
        entries = json.load(open(DISCOVERY))
    except (OSError, ValueError):
        return 13710
    for entry in entries:
        if entry.get("pluginName") == "OsTIrus":
            return entry["port"]
    return 13710


def http(port, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
    # Some servers wrap responses as server-sent events: take the last "data:" line.
    if body.lstrip().startswith(("event:", "data:")):
        lines = [l[5:].strip() for l in body.splitlines() if l.startswith("data:")]
        body = lines[-1] if lines else "{}"
    return json.loads(body) if body.strip() else {}


def rpc(port, method, params=None, ident=1):
    return http(port, "/mcp", {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}})


def call(port, tool, args=None):
    rpc(port, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "ti-panel-tools", "version": "1.0"}})
    reply = rpc(port, "tools/call", {"name": tool, "arguments": args or {}}, ident=2)
    if "error" in reply:
        raise SystemExit(f"{tool} failed: {reply['error']}")
    result = reply.get("result", {})
    texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    if result.get("isError"):
        raise SystemExit(f"{tool} error: {' '.join(texts)}")
    return "\n".join(texts)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    port = find_port()
    cmd = sys.argv[1]

    if cmd == "health":
        print(json.dumps(http(port, "/health"), indent=2))
    elif cmd == "tools":
        rpc(port, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                  "clientInfo": {"name": "ti-panel-tools", "version": "1.0"}})
        for tool in rpc(port, "tools/list", ident=2).get("result", {}).get("tools", []):
            print(f"{tool['name']:28} {tool.get('description', '')[:90]}")
    elif cmd == "call":
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(call(port, sys.argv[2], args))
    elif cmd == "reload":
        print(call(port, "send_key", {"key": "f5"}))
        print(call(port, "get_dialogs"))
    elif cmd == "shot":
        text = call(port, "screenshot")
        path = next((w for w in text.replace('"', " ").split() if w.endswith(".png")), None)
        if path is None:
            raise SystemExit(f"no PNG path in reply: {text}")
        if len(sys.argv) > 2:
            shutil.copy(path, sys.argv[2])
            path = sys.argv[2]
        print(path)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
