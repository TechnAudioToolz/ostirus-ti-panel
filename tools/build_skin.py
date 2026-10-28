#!/usr/bin/env python3
"""Builds the TI Panel skin from the untouched TrancyTI files in reference/.

    python3 tools/build_skin.py      (run gen_art first, see README)

What it does:
  - copies TrancyTI's assets into skin/TIPanel (minus the old knob sprite sheets)
  - points TrancyTI's knob classes at the dark knobs from gen_art, so its edit pages match
  - keeps every element OsTIrus finds by id (PatchName, Menu, PresetPrev, the part list...)
  - replaces the tabbed main page with a Virus TI style front panel (LAYOUT below)
  - wraps TrancyTI's edit pages and the patch browser in full-window overlays (tab group "pages")
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference" / "TrancyTI"
OUT = ROOT / "skin" / "TIPanel"
W, H = 2638, 1301

# --------------------------------------------------------------------------------------------
# Tolerant RML element finder: attribute values contain '>' (">=" in conditions), so tags are
# matched with quoted strings in mind, and an element's extent is found by nesting depth.

TAG = re.compile(r'<(/?)([A-Za-z][\w-]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*?)(/?)>', re.S)


def top_level_children(text, start, end):
    """(start, end, name, attrs) of the direct children between start and end."""
    children, depth, open_at = [], 0, None
    for m in TAG.finditer(text, start, end):
        closing, name, attrs, selfclose = m.groups()
        if closing:
            depth -= 1
            if depth == 0:
                children.append((open_at[0], m.end(), open_at[1], open_at[2]))
            continue
        if depth == 0:
            if selfclose:
                children.append((m.start(), m.end(), name, attrs))
                continue
            open_at = (m.start(), name, attrs)
        if not selfclose:
            depth += 1
    return children


def attr(attrs, name):
    m = re.search(r'\b' + re.escape(name) + r'="([^"]*)"', attrs)
    return m.group(1) if m else None


def set_attr(tag_text, name, value):
    """Set (or remove, with value None) an attribute in an element's opening tag."""
    head_end = TAG.match(tag_text).end()
    head, rest = tag_text[:head_end], tag_text[head_end:]
    head = re.sub(r'\s' + re.escape(name) + r'="[^"]*"', '', head)
    if value is not None:
        head = re.sub(r'(/?>)$', f' {name}="{value}"\\1', head)
    return head + rest


def set_style(tag_text, **props):
    """Change style properties (left=..., top=...) in an element's opening tag."""
    head_end = TAG.match(tag_text).end()
    head, rest = tag_text[:head_end], tag_text[head_end:]
    style = attr(head, "style") or ""
    for key, value in props.items():
        key = key.replace("_", "-")
        style = re.sub(r'(^|;)\s*' + re.escape(key) + r'\s*:[^;]*', r'\1', style).strip("; ")
        if value is not None:
            style = (style + "; " if style else "") + f"{key}: {value}"
    return set_attr(head, "style", style + ";") + rest


# --------------------------------------------------------------------------------------------
# Panel element helpers. Coordinates are in dp, relative to the enclosing section.

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(x, y, w, h):
    return f"left: {x}dp; top: {y}dp; width: {w}dp; height: {h}dp;"


KNOB = {"L": "hwknobL", "M": "hwknobM", "S": "hwknobS"}
KNOB_SIZE = {"L": 168, "M": 132, "S": 100}


def label(text, x, y, w, size=22, cls="hwLabel"):
    return f'<div class="jucePos {cls}" style="{box(x, y, w, 30)} font-size: {size}dp;">{esc(text)}</div>'


def knob(eid, param, text, x, y, size="M", px=None):
    """Knob with its caption centred above it. (x, y) is the knob's top-left."""
    d = px or KNOB_SIZE[size]
    out = [f'<knob id="{eid}" class="jucePos juceRotary {KNOB[size]}" data-model="partCurrent" param="{param}" style="{box(x, y, d, d)}"/>']
    if text:
        out.insert(0, label(text, x - 30, y - 30, d + 60))
    return "\n".join(out)


def combo(eid, param, text, x, y, w, h=46):
    out = [f'<combo id="{eid}" class="jucePos hwCombo" data-model="partCurrent" param="{param}" style="{box(x, y, w, h)} line-height: {h}dp;"><combotext>-</combotext></combo>']
    if text:
        out.insert(0, label(text, x, y - 30, w))
    return "\n".join(out)


def ledkey(eid, text, x, y, param=None, value_on=None, tab=None):
    """Rubber key with an LED above it. Either bound to a parameter or a tab button."""
    attrs = 'isToggle="1"'
    if param:
        attrs += f' data-model="partCurrent" param="{param}"'
        if value_on is not None:
            attrs += f' valueOn="{value_on}"'
    if tab:
        attrs += f' tabgroup="{tab[0]}" tabbutton="{tab[1]}"'
    return (f'<button id="{eid}" class="jucePos juceButton hwledkey" {attrs} style="{box(x, y, 88, 76)}">'
            f'<div class="hwKeyText" style="{box(6, 28, 76, 44)} line-height: 44dp;">{esc(text)}</div></button>')


def key(eid, text, x, y, tab=None, extra=""):
    attrs = f'tabgroup="{tab[0]}" tabbutton="{tab[1]}" isToggle="1"' if tab else ""
    return (f'<button id="{eid}" class="jucePos juceButton hwkey" {attrs} {extra} style="{box(x, y, 88, 50)}">'
            f'<div class="hwKeyText" style="{box(6, 3, 76, 44)} line-height: 44dp;">{esc(text)}</div></button>')


def led(eid, text, x, y, w, tab=None, param=None, value_on=None):
    """LED with a printed label beside it, like the hardware's destination and FX lists."""
    attrs = 'isToggle="1"'
    if param:
        attrs += f' data-model="partCurrent" param="{param}"'
        if value_on is not None:
            attrs += f' valueOn="{value_on}"'
    if tab:
        attrs += f' tabgroup="{tab[0]}" tabbutton="{tab[1]}"'
    return (f'<button id="{eid}" class="jucePos juceButton hwled" {attrs} style="{box(x, y, w, 36)}">'
            f'<div class="hwLedText" style="padding-left: 40dp; height: 36dp; line-height: 36dp;">{esc(text)}</div></button>')


def page(group, index, w, h, children):
    return (f'<div class="jucePos" tabgroup="{group}" tabpage="{index}" style="{box(0, 0, w, h)}">\n'
            + "\n".join(children) + "\n</div>")


def section(sid, title, x, y, w, h, children, title_w=None):
    tw = title_w or min(w - 40, 40 + 17 * len(title))
    # Selector pages cover the whole section, so they go first: anything after them (the
    # select buttons, EDIT, shared knobs) is drawn on top and still receives clicks.
    children = sorted(children, key=lambda c: 'tabpage="' not in c.split(">", 1)[0])
    return (f'<div id="{sid}" class="jucePos hwSection" style="{box(x, y, w, h)}">\n'
            f'<div class="jucePos hwTitle" style="{box((w - tw) // 2, 14, tw, 38)} line-height: 38dp;">{esc(title)}</div>\n'
            + "\n".join(children) + "\n</div>")


# --------------------------------------------------------------------------------------------
# The front panel, laid out like the Virus TI desktop: matrix/arp/effects on the left,
# modulators and oscillators across the top, the display in the middle, the mixer column,
# then filters and both envelopes on the right.

MATRIX = [
    # (source, (dest1, dest2, dest3), (amount1, amount2, amount3)) - spellings vary per slot
    ("Assign1 Source", ("Assign1 Destination", "Assign 1 Destination 2", "Assign 1 Destination 3"),
     ("Assign1 Amount", "Assign 1 Amount 2", "Assign 1 Amount 3")),
    ("Assign2 Source", ("Assign2 Destination1", "Assign2 Destination2", "Assign 2 Destination 3"),
     ("Assign2 Amount1", "Assign2 Amount2", "Assign 2 Amount 3")),
    ("Assign3 Source", ("Assign3 Destination1", "Assign3 Destination2", "Assign3 Destination3"),
     ("Assign3 Amount1", "Assign3 Amount2", "Assign3 Amount3")),
] + [
    (f"Assign {n} Source", (f"Assign {n} Destination", f"Assign {n} Destination 2", f"Assign {n} Destination 3"),
     (f"Assign {n} Amount", f"Assign {n} Amount 2", f"Assign {n} Amount 3")) for n in (4, 5, 6)
]

LFO_AMOUNTS = {
    1: [("OSC 1", "Osc1 Lfo1 Amount"), ("OSC 2", "Osc2 Lfo1 Amount"), ("PW", "PW Lfo1 Amount"),
        ("RESO", "Reso Lfo1 Amount"), ("F.GAIN", "FiltGain Lfo1 Amount")],
    2: [("CUTOFF 1", "Cutoff1 Lfo2 Amount"), ("CUTOFF 2", "Cutoff2 Lfo2 Amount"), ("SHAPE", "Shape Lfo2 Amount"),
        ("FM", "FM Lfo2 Amount"), ("PAN", "Pan Lfo2 Amount")],
}

FX_A = [  # name, (caption, param) x3
    ("DELAY", [("SEND", "Delay Send"), ("TIME", "Delay Time"), ("FEEDBACK", "Delay Feedback")]),
    ("REVERB", [("SEND", "Reverb Send"), ("TIME", "Reverb Time"), ("DAMPING", "Reverb Damping")]),
    ("LOW EQ", [("GAIN", "LowEQ Gain"), ("FREQ", "LowEQ Frequency"), None]),
    ("MID EQ", [("GAIN", "MidEQ Gain"), ("FREQ", "MidEQ Frequency"), ("Q", "MidEQ Q-Factor")]),
    ("HIGH EQ", [("GAIN", "HighEQ Gain"), ("FREQ", "HighEQ Frequency"), None]),
]
FX_B = [
    ("DISTORTION", [("TYPE", "Distortion Curve", "combo"), ("INTENSITY", "Distortion Intensity"), ("MIX", "Patch Distortion/Mix")]),
    ("CHARACTER", [("TYPE", "Character Type", "combo"), ("BASS", "Bass Intensity"), ("TUNE", "Bass Tune")]),
    ("CHORUS", [("MIX", "Chorus Mix"), ("RATE", "Chorus Rate"), ("DEPTH", "Chorus Depth")]),
    ("PHASER", [("MIX", "Phaser Mix"), ("RATE", "Phaser Rate"), ("DEPTH", "Phaser Depth")]),
]

# Indices of TrancyTI's "pages" tab group, which OsTIrus also uses.
PAGE = {"main": 0, "browser": 1, "osc": 2, "filter": 3, "lfo": 4, "matrix": 5, "arp": 6, "fx1": 7, "fx2": 8, "common": 9, "multi": 10}


def build_panel():
    parts = []

    # Brand + volume
    parts.append(section("hwBrand", "VOLUME", 30, 30, 220, 300, [
        knob("hwVolume", "Master Volume", "", 26, 92, "L"),
        f'<div class="jucePos hwBrand" style="{box(0, 266, 220, 34)}">OsTIrus · TI PANEL</div>',
    ]))

    # Matrix: slot selector + source/destinations/amounts of the selected slot
    pages = []
    for i, (src, dests, amts) in enumerate(MATRIX):
        kids = [combo(f"hwMatSrc{i}", src, "SOURCE", 150, 82, 250)]
        for k in range(3):
            kids.append(combo(f"hwMatDst{i}{k}", dests[k], "", 150, 140 + k * 52, 190, 44))
            kids.append(knob(f"hwMatAmt{i}{k}", amts[k], "", 350, 134 + k * 52, px=54))
        pages.append(page("hwSlot", i, 440, 300, kids))
    parts.append(section("hwMatrix", "MATRIX", 260, 30, 440, 300,
                         [led(f"hwSlot{i}", f"SLOT {i + 1}", 16, 66 + i * 38, 130, tab=("hwSlot", i)) for i in range(6)]
                         + pages + [key("hwMatEdit", "EDIT", 340, 8, tab=("pages", PAGE["matrix"]))]))

    # Arpeggiator
    parts.append(section("hwArp", "ARPEGGIATOR", 30, 350, 670, 250, [
        combo("hwArpMode", "Arp Mode", "MODE", 20, 96, 150),
        combo("hwArpPattern", "Arp Pattern Selct", "PATTERN", 182, 96, 150),
        combo("hwArpOct", "Arp Octave Range", "OCTAVES", 344, 96, 120),
        combo("hwArpClock", "Arp Clock", "CLOCK", 476, 96, 174),
        ledkey("hwArpHold", "HOLD", 30, 160, param="Arp Hold Enable"),
        knob("hwArpLen", "Arp Note Length", "LENGTH", 230, 172, px=70),
        knob("hwArpSwing", "Arp Swing", "SWING", 370, 172, px=70),
        key("hwArpEdit", "EDIT", 562, 186, tab=("pages", PAGE["arp"])),
    ]))

    # Effects A: delay / reverb / EQ
    pages = []
    for i, (_, knobs) in enumerate(FX_A):
        kids = [knob(f"hwFxA{i}_{k}", p[1], p[0], 230 + k * 145, 120, "S") for k, p in enumerate(knobs) if p]
        pages.append(page("hwFxA", i, 670, 320, kids))
    parts.append(section("hwFxASec", "EFFECTS", 30, 620, 670, 320,
                         [led(f"hwFxASel{i}", name, 20, 70 + i * 44, 170, tab=("hwFxA", i)) for i, (name, _) in enumerate(FX_A)]
                         + pages + [key("hwFxAEdit", "EDIT", 562, 250, tab=("pages", PAGE["fx2"]))]))

    # Effects B: distortion / character / chorus / phaser
    pages = []
    for i, (_, ctrls) in enumerate(FX_B):
        kids = []
        for k, c in enumerate(ctrls):
            if len(c) == 3:
                kids.append(combo(f"hwFxB{i}_{k}", c[1], c[0], 205 + k * 145, 150, 150))
            else:
                kids.append(knob(f"hwFxB{i}_{k}", c[1], c[0], 230 + k * 145, 120, "S"))
        pages.append(page("hwFxB", i, 670, 311, kids))
    parts.append(section("hwFxBSec", "EFFECTS 2", 30, 960, 670, 311,
                         [led(f"hwFxBSel{i}", name, 20, 70 + i * 44, 180, tab=("hwFxB", i)) for i, (name, _) in enumerate(FX_B)]
                         + pages + [key("hwFxBEdit", "EDIT", 562, 245, tab=("pages", PAGE["fx1"]))]))

    # Modulators: LFO select, rate/shape/clock, then the selected LFO's destination amounts
    pages = []
    for n in (1, 2, 3):
        kids = [
            knob(f"hwLfoRate{n}", f"Lfo{n} Rate", "RATE", 30, 200, "L"),
            combo(f"hwLfoShape{n}", f"Lfo{n} Shape", "SHAPE", 230, 200, 190),
            combo(f"hwLfoClock{n}", f"Lfo{n} Clock", "CLOCK", 230, 282, 190),
        ]
        if n in LFO_AMOUNTS:
            kids.append(ledkey(f"hwLfoEnv{n}", "ENV MODE", 230, 340, param=f"Lfo{n} Env Mode"))
            kids.append(ledkey(f"hwLfoTrig{n}", "KEY TRIG", 332, 340, param=f"Lfo{n} Keytrigger"))
            for k, (cap, prm) in enumerate(LFO_AMOUNTS[n]):
                kids.append(knob(f"hwLfoAmt{n}{k}", prm, cap, 22 + k * 82, 468, px=64))
            kids.append(combo(f"hwLfoAssign{n}", f"LFO{n} Assign Dest", "ASSIGN", 20, 562, 250))
            kids.append(knob(f"hwLfoAssignAmt{n}", f"LFO{n} Assign Amount", "", 290, 552, px=64))
        else:
            kids.append(combo("hwLfo3Dest", "Lfo3 Destination", "DESTINATION", 20, 470, 250))
            kids.append(knob("hwLfo3Amt", "Osc Lfo3 Amount", "AMOUNT", 300, 455, px=80))
            kids.append(knob("hwLfo3Fade", "Lfo3 Fade-In Time", "FADE IN", 300, 580, px=64))
        pages.append(page("hwLfo", n - 1, 440, 650, kids))
    parts.append(section("hwLfoSec", "MODULATORS", 720, 30, 440, 650,
                         [ledkey(f"hwLfoSel{n}", f"LFO {n}", 20 + (n - 1) * 92, 66, tab=("hwLfo", n - 1)) for n in (1, 2, 3)]
                         + pages + [key("hwLfoEdit", "EDIT", 334, 80, tab=("pages", PAGE["lfo"]))]))

    # Oscillators
    pages = []
    for n in (1, 2, 3):
        if n < 3:
            kids = [
                combo(f"hwOscMode{n}", f"Osc{n} Mode", "MODEL", 290, 96, 260),
                knob(f"hwOscShape{n}", f"Osc{n} Shape", "SHAPE", 30, 230, "M"),
                knob(f"hwOscWave{n}", f"Osc{n} Wave Select", "WAVE SEL", 200, 230, "M"),
                knob(f"hwOscPw{n}", f"Osc{n} Pulsewidth", "PW", 370, 230, "M"),
                knob(f"hwOscSemi{n}", f"Osc{n} Semitone", "SEMITONE", 30, 440, "M"),
            ]
            if n == 2:
                kids += [knob("hwOscDetune2", "Osc2 Detune", "DETUNE", 200, 440, "M"),
                         knob("hwOscFm2", "Osc2 FM Amount", "FM AMOUNT", 370, 440, "M"),
                         ledkey("hwOscSync2", "SYNC", 590, 96, param="Osc2 Sync")]
            else:
                kids.append(knob("hwOscKey1", "Osc1 Keyfollow", "KEYFOLLOW", 200, 440, "M"))
        else:
            kids = [
                combo("hwOscMode3", "Osc3 Mode", "MODEL", 290, 96, 260),
                knob("hwOsc3Vol", "Osc3 Volume", "VOLUME", 30, 230, "M"),
                knob("hwOscSemi3", "Osc3 Semitone", "SEMITONE", 30, 440, "M"),
                knob("hwOscDetune3", "Osc3 Detune", "DETUNE", 200, 440, "M"),
            ]
        pages.append(page("hwOsc", n - 1, 700, 650, kids))
    parts.append(section("hwOscSec", "OSCILLATORS", 1180, 30, 700, 650,
                         [ledkey(f"hwOscSel{n}", f"OSC {n}", 20 + (n - 1) * 92, 66, tab=("hwOsc", n - 1)) for n in (1, 2, 3)]
                         + pages + [
                             combo("hwUnison", "Unison Mode", "UNISON", 540, 250, 140),
                             knob("hwUniDetune", "Unison Detune", "U.DETUNE", 548, 362, px=64),
                             combo("hwKeyMode", "Key Mode", "KEY MODE", 540, 470, 140),
                             knob("hwGlide", "Portamento Time", "GLIDE", 548, 562, px=64),
                             key("hwOscEdit", "EDIT", 592, 8, tab=("pages", PAGE["osc"])),
                         ]))

    # Mixer column
    mix = [("OSC BAL", "Osc Balance"), ("SUB OSC", "Suboscillator Volume"), ("OSC VOL", "Osc Mainvolume"),
           ("NOISE", "Noise Volume"), ("RING MOD", "Ringmodulator Volume")]
    parts.append(section("hwMixSec", "MIXER", 1900, 30, 160, 1241,
                         [knob(f"hwMix{i}", p, cap, 14, 120 + i * 225, "M") for i, (cap, p) in enumerate(mix)], title_w=120))

    # Filters
    pages = []
    for n in (1, 2):
        pages.append(page("hwFilt", n - 1, 528, 650, [
            combo(f"hwFiltMode{n}", f"Filter{n} Mode", "MODE", 200, 96, 220),
            knob(f"hwFiltReso{n}", f"Filter{n} Resonance", "RESONANCE", 220, 240, "M"),
            knob(f"hwFiltEnv{n}", f"Filter{n} Env Amt", "ENV AMOUNT", 372, 240, "M"),
            knob(f"hwFiltKey{n}", f"Filter{n} Keyfollow", "KEYTRACK", 232, 450, "S"),
        ]))
    parts.append(section("hwFiltSec", "FILTERS", 2080, 30, 528, 650,
                         [ledkey(f"hwFiltSel{n}", f"FILT {n}", 18 + (n - 1) * 92, 66, tab=("hwFilt", n - 1)) for n in (1, 2)]
                         + pages + [
                             knob("hwCutoff", "Cutoff", "CUTOFF", 22, 210, "L"),
                             knob("hwCutoff2", "Cutoff2", "CUTOFF 2", 38, 440, "M"),
                             knob("hwFiltBal", "Filter Balance", "BALANCE", 372, 450, "S"),
                             combo("hwRouting", "Filter Routing", "ROUTING", 200, 590, 300),
                             key("hwFiltEdit", "EDIT", 428, 8, tab=("pages", PAGE["filter"])),
                         ]))

    # Envelopes
    for sid, title, y, prefix in (("hwFEnv", "FILTER ENVELOPE", 700, "Filter Env"), ("hwAEnv", "AMPLIFIER ENVELOPE", 990, "Amp Env")):
        stages = [("ATTACK", "Attack"), ("DECAY", "Decay"), ("SUSTAIN", "Sustain"), ("TIME", "Sustain Time"), ("RELEASE", "Release")]
        parts.append(section(sid, title, 2080, y, 528, 281 if y == 990 else 270,
                             [knob(f"{sid}{k}", f"{prefix} {p}", cap, 14 + k * 102, 120, px=90) for k, (cap, p) in enumerate(stages)]))

    return "\n".join(parts)


# --------------------------------------------------------------------------------------------

def build_display(globals_):
    """The centre display. Reuses OsTIrus's own elements (by id) so the patch name, the focused
    parameter readout and the preset buttons keep working."""
    dx, dy, dw, dh = 720, 700, 1160, 571
    g = {}
    for k, v in globals_.items():
        g[k] = v
    kids = []
    lcd = (190, 30, 780, 290)
    kids.append(f'<div id="hwLcd" class="jucePos hwLcd" ondblclick="openBrowser()" title="Double-click to browse patches" style="{box(*lcd)}">')
    kids.append(set_style(g["PatchName"], left="30dp", top="26dp", width="720dp", height="70dp", line_height="70dp",
                          color="#16202a", font_size="54dp", text_align="left"))
    kids.append(set_style(g["FocusedParameterName"], left="30dp", top="130dp", width="460dp", height="50dp", line_height="50dp",
                          color="#16202a", font_size="34dp", text_align="left"))
    kids.append(set_style(g["FocusedParameterValue"], left="490dp", top="130dp", width="260dp", height="50dp", line_height="50dp",
                          color="#16202a", font_size="34dp", text_align="right"))
    kids.append(f'<div class="jucePos hwLcdHint" style="{box(30, 226, 720, 40)} line-height: 40dp;">DOUBLE-CLICK TO BROWSE PATCHES</div>')
    kids.append("</div>")

    def as_key(tag_text, text, x, y, ledkey_=False):
        cls = "hwledkey" if ledkey_ else "hwkey"
        tag_text = re.sub(r'class="[^"]*"', f'class="jucePos juceButton {cls}"', tag_text, count=1)
        tag_text = set_style(tag_text, left=f"{x}dp", top=f"{y}dp", width="88dp", height=f"{76 if ledkey_ else 50}dp")
        ty = 28 if ledkey_ else 3
        inner = f'<div class="hwKeyText" style="{box(6, ty, 76, 44)} line-height: 44dp;">{esc(text)}</div>'
        if tag_text.endswith("/>"):
            return tag_text[:-2] + ">" + inner + "</button>"
        return tag_text.replace("</button>", inner + "</button>")

    kids.append(as_key(g["PresetPrev"], "PREV", 60, 60))
    kids.append(as_key(g["PresetNext"], "NEXT", 60, 130))
    kids.append(key("hwBrowse", "BROWSE", 1010, 40, tab=("pages", PAGE["browser"])))
    kids.append(as_key(g["PresetLoad"], "LOAD", 1010, 110))
    kids.append(as_key(g["PresetSave"], "SAVE", 1010, 180))
    kids.append(as_key(g["Menu"], "MENU", 1010, 250))
    kids.append(as_key(g["PlayModeSingle"], "SINGLE", 30, 230, ledkey_=True))
    kids.append(as_key(g["PlayModeMulti"], "MULTI", 30, 320, ledkey_=True))
    kids.append(key("hwParts", "PARTS", 30, 420, tab=("pages", PAGE["multi"])))
    kids.append(key("hwCommon", "COMMON", 30, 490, tab=("pages", PAGE["common"])))

    # VALUE 1-3: the patch's soft knobs, with what they control chosen above each one.
    for i in range(3):
        x = 250 + i * 230
        kids.append(combo(f"hwSoftName{i}", f"Soft Knob{i + 1} ShortName Main", "", x - 30, 352, 190, 42))
        kids.append(knob(f"hwSoft{i}", f"Soft Knob Configuration/Value Softknob{i}", "", x, 410, "M"))
        kids.append(label(f"VALUE {i + 1}", x - 30, 548, 190, 20))
    kids.append(knob("hwTranspose", "Transpose", "TRANSPOSE", 960, 400, "S"))

    return (f'<div id="hwDisplay" class="jucePos hwDisplay" style="{box(dx, dy, dw, dh)}">\n' + "\n".join(kids) + "\n</div>")


def overlay(eid, index, title, inner, frame):
    fx, fy, fw, fh = frame
    return (f'<div id="{eid}" class="jucePos hwOverlay" tabgroup="pages" tabpage="{index}" style="{box(0, 0, W, H)}">\n'
            f'<div class="jucePos hwOverlayFrame" style="{box(fx, fy, fw, fh)}"></div>\n'
            f'<div class="jucePos hwOverlayTitle" style="{box(fx + 30, fy + 18, 900, 48)} line-height: 48dp;">{esc(title)}</div>\n'
            + inner + "\n"
            # OsTIrus wires only one button per tab index, so every CLOSE presses the shared
            # hidden "hwCloseTab" button through the skin script instead.
            + f'<div id="{eid}Close" class="jucePos hwCloseBtn" onclick="closeOverlay()" style="{box(fx + fw - 250, fy + 14, 220, 72)} line-height: 72dp;">CLOSE</div>\n'
            + "</div>")


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # Assets, without the old knob sheets (their names would clash with nothing, but they're 9 MB).
    for f in REF.iterdir():
        if f.is_file() and not f.name.startswith("knob_") and f.suffix not in (".rml", ".rcss"):
            shutil.copy2(f, OUT / f.name)

    # ---- RCSS: drop old knob sheets, aim the knob classes at the dark knobs, add panel styles.
    rcss = (REF / "VirusTI_Trancy.rcss").read_text()
    rcss = re.sub(r'@spritesheet knob_\w+\s*\{[^}]*\}\s*', '', rcss)
    for old, new in (("knob_small_ring_", "hwk_t128_"), ("knob_big_ring_", "hwk_t223_"),
                     ("knob_small_", "hwk_t70_"), ("knob_mid_", "hwk_t98_")):
        rcss = rcss.replace(f"spriteprefix: {old};", f"spriteprefix: {new};")
    rcss += "\n" + (ROOT / "tools" / "panel.rcss").read_text()
    (OUT / "TIPanel.rcss").write_text(rcss)

    # ---- RML
    rml = (REF / "VirusTI_Trancy.rml").read_text()
    rml = rml.replace('href="VirusTI_Trancy.rcss"/>',
                      'href="TIPanel.rcss"/>\n\t\t<link type="text/rcss" href="hw_art.rcss"/>\n\t\t<script src="TIPanel.lua"></script>')
    body_open = re.search(r'<body[^>]*>', rml)
    body_close = rml.rindex("</body>")
    children = top_level_children(rml, body_open.end(), body_close)

    drop = {"bg", "logolight", "logo"}
    keep_ids = {"PatchName", "FocusedParameterValue", "FocusedParameterName", "Menu", "PlayModeSingle",
                "PlayModeMulti", "PresetPrev", "PresetNext", "PresetSave", "PresetLoad"}
    globals_, part_list, pages = {}, [], {}
    for start, end, name, attrs in children:
        text = rml[start:end]
        eid = attr(attrs, "id") or ""
        if eid in drop or (attr(attrs, "tabgroup") == "pages" and attr(attrs, "tabbutton") is not None):
            continue
        if attr(attrs, "tabgroup") == "pages" and attr(attrs, "tabpage") is not None:
            pages[int(attr(attrs, "tabpage"))] = text
        elif eid in keep_ids:
            globals_[eid] = text
        else:
            part_list.append(text)  # the 16-part list and its containers

    missing = keep_ids - globals_.keys()
    assert not missing, f"TrancyTI elements not found: {missing}"
    assert set(pages) == set(range(11)), f"unexpected pages: {sorted(pages)}"

    def strip_tab(text, **style):
        text = set_attr(text, "tabgroup", None)
        text = set_attr(text, "tabpage", None)
        return set_style(text, **style) if style else text

    body = [f'<div id="hwBg" class="jucePos hwPanel" style="{box(0, 0, W, H)}"></div>',
            build_panel(),
            build_display(globals_),
            # page 0: nothing open
            f'<div id="hwNoOverlay" class="jucePos" tabgroup="pages" tabpage="0" style="{box(0, 0, 1, 1)}"></div>',
            f'<button id="hwCloseTab" class="jucePos juceButton" isToggle="1" tabgroup="pages" tabbutton="0" style="{box(0, 0, 1, 1)}"></button>']

    titles = {2: "OSCILLATORS", 3: "FILTERS", 4: "MODULATORS", 5: "MOD MATRIX", 6: "ARPEGGIATOR",
              7: "EFFECTS 1", 8: "EFFECTS 2", 9: "COMMON", 10: "MULTI / PARTS"}
    frame = (300, 50, 2038, 1180)
    for i in range(2, 10):
        body.append(overlay(f"hwOvl{i}", i, titles[i], strip_tab(pages[i], left="333dp", top="130dp"), frame))
    # Multi: TrancyTI's part list on the left, its multi page beside it, as in the original.
    body.append(overlay("hwOvl10", 10, titles[10], "\n".join(part_list) + "\n" + strip_tab(pages[10]), (40, 30, 2558, 1241)))
    # Browser: the patch manager, expanded to nearly the whole window.
    browser = strip_tab(pages[1], left="354dp", top="120dp", width="1930dp", height="1120dp", decorator=None)
    body.append(overlay("hwOvl1", 1, "PATCH BROWSER", browser, (40, 30, 2558, 1241)))

    rml = rml[:body_open.end()] + "\n" + "\n".join(body) + "\n" + rml[body_close:]
    (OUT / "TIPanel.rml").write_text(rml)
    shutil.copy2(ROOT / "tools" / "TIPanel.lua", OUT / "TIPanel.lua")

    # Every parameter the panel binds must exist in TrancyTI (a typo would silently do nothing).
    known = set(re.findall(r'param="([^"]+)"', (REF / "VirusTI_Trancy.rml").read_text()))
    used = set(re.findall(r'param="([^"]+)"', rml))
    unknown = sorted(used - known)
    print(f"wrote {OUT/'TIPanel.rml'} ({len(rml)//1024} KB), {len(used)} parameters bound")
    if unknown:
        print("WARNING - not found in TrancyTI, check the spelling:", ", ".join(unknown))


if __name__ == "__main__":
    build()
