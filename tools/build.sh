#!/bin/sh
# Rebuild the TI Panel skin: panel markup from TrancyTI + generated artwork.
set -e
cd "$(dirname "$0")/.."
mkdir -p build
[ -f reference/TrancyTI/VirusTI_Trancy.rml ] || python3 -I tools/fetch_trancyti.py
[ build/gen_art -nt tools/gen_art.swift ] || swiftc -O tools/gen_art.swift -o build/gen_art
[ build/retint -nt tools/retint.swift ] || swiftc -O tools/retint.swift -o build/retint
python3 -I tools/build_skin.py
./build/gen_art skin/TIPanel
# Darken TrancyTI's light-grey edit page artwork to sit with the charcoal panel.
./build/retint 1.0 skin/TIPanel/panel_*.png skin/TIPanel/filter_mode_routing_*.png skin/TIPanel/button_disable.png
