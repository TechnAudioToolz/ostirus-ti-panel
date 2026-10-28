# TI Panel — a Virus TI hardware-style skin for OsTIrus

A skin for [OsTIrus](https://github.com/dsp56300/gearmulator) (gearmulator's Virus TI emulator) that
puts the synth on one page, laid out like the Virus TI desktop's front panel, with dark knobs, red
LEDs and an LCD. The detailed edit pages open as pop-ups; double-click the LCD to browse patches.

Made for OsTIrus 2.2.27. Built from its TrancyTI skin (GPL-3.0), so this skin is GPL-3.0 as well.

## Build and install (macOS)

Needs Python 3 and Swift (comes with Xcode or the Xcode Command Line Tools).

```sh
tools/build.sh
ln -s "$PWD/skin/TIPanel" "$HOME/Documents/The Usual Suspects/OsTIrus/skins/TIPanel"
```

The first build downloads the TrancyTI skin files from gearmulator into `reference/TrancyTI`. They
aren't stored in this repo, partly because TrancyTI's two fonts carry no license of their own.

Then in OsTIrus: Menu → Settings → Skins → Activate **TIPanel**. Reopen the plugin window to load
changes.

## How it's made

- `tools/fetch_trancyti.py` downloads TrancyTI from gearmulator (tag 2.2.27)
- `tools/build_skin.py` builds the front panel and moves TrancyTI's pages into pop-ups
- `tools/gen_art.swift` draws the knobs, keys and LEDs
- `tools/retint.swift` recolours TrancyTI's light-grey edit pages to dark panels with white print
- `tools/TIPanel.lua` double-click-to-browse and the shared CLOSE button

## Testing

These drive a running OsTIrus through its built-in MCP server (Settings → Skins → Enable MCP Server):

- `tools/test_wiring.py` — every knob moves its parameter
- `tools/test_controls.py` — select buttons, toggles, drop-down menus
- `tools/test_overlays.py` — every pop-up opens and closes

## Credits

- [gearmulator](https://github.com/dsp56300/gearmulator) by dsp56300 and contributors: the OsTIrus
  emulator and the TrancyTI skin this is built from.
- OsTIrus needs a Virus TI firmware image you provide yourself; none is included here.

Not affiliated with or endorsed by Access Music. Virus and Virus TI are trademarks of their owners.
