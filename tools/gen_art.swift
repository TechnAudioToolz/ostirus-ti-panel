// Generates the TI Panel skin artwork: knob sprite sheets, LED buttons and keys, plus the RCSS
// that names every frame. Run from the project root:
//
//     swift tools/gen_art.swift skin/TIPanel
//
// Everything is drawn in code, so re-tinting the whole skin is a change to the colours below.

import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let outDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "skin/TIPanel"

// MARK: - Palette (Virus TI hardware: charcoal body, black knobs, white print, red LEDs)

func rgb(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 0xff) / 255, green: CGFloat((hex >> 8) & 0xff) / 255,
            blue: CGFloat(hex & 0xff) / 255, alpha: alpha)
}

let tickColour = rgb(0xb9bcc0)
let arcTrack = rgb(0x1c1d20)
let arcValue = rgb(0xe23b2e)
let pointerColour = rgb(0xf4f4f4)
let ledOff = rgb(0x4a1512)
let ledOn = rgb(0xff3b2b)

// MARK: - Drawing helpers (top-left origin, y down)

func makeContext(_ width: Int, _ height: Int) -> CGContext {
    let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.translateBy(x: 0, y: CGFloat(height))
    ctx.scaleBy(x: 1, y: -1)
    ctx.setShouldAntialias(true)
    ctx.interpolationQuality = .high
    return ctx
}

func savePNG(_ ctx: CGContext, _ name: String) {
    let url = URL(fileURLWithPath: outDir).appendingPathComponent(name) as CFURL
    let dest = CGImageDestinationCreateWithURL(url, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
}

// Angle 0 = 12 o'clock, clockwise positive (same as a knob).
func point(_ c: CGPoint, _ r: CGFloat, _ degrees: CGFloat) -> CGPoint {
    let a = degrees * .pi / 180
    return CGPoint(x: c.x + r * sin(a), y: c.y - r * cos(a))
}

func arcPath(_ c: CGPoint, _ r: CGFloat, from: CGFloat, to: CGFloat) -> CGPath {
    let path = CGMutablePath()
    let steps = max(2, Int(abs(to - from) / 2))
    for i in 0...steps {
        let p = point(c, r, from + (to - from) * CGFloat(i) / CGFloat(steps))
        i == 0 ? path.move(to: p) : path.addLine(to: p)
    }
    return path
}

func radialFill(_ ctx: CGContext, centre: CGPoint, radius: CGFloat, inner: CGColor, outer: CGColor, offset: CGPoint) {
    let gradient = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: [inner, outer] as CFArray, locations: [0, 1])!
    ctx.saveGState()
    ctx.addEllipse(in: CGRect(x: centre.x - radius, y: centre.y - radius, width: radius * 2, height: radius * 2))
    ctx.clip()
    ctx.drawRadialGradient(gradient, startCenter: CGPoint(x: centre.x + offset.x, y: centre.y + offset.y), startRadius: 0,
                           endCenter: centre, endRadius: radius * 1.05, options: [.drawsAfterEndLocation])
    ctx.restoreGState()
}

// MARK: - Knob

// One frame: printed 0-12 scale, red value arc, black knob with a white pointer.
func drawKnob(_ ctx: CGContext, origin: CGPoint, size: CGFloat, value: CGFloat) {
    let c = CGPoint(x: origin.x + size / 2, y: origin.y + size / 2)
    let r = size / 2
    let start: CGFloat = -135, sweep: CGFloat = 270
    let angle = start + sweep * value

    // Printed scale: 13 ticks like the hardware's 0..12, the ends and middle a little longer.
    ctx.setLineCap(.round)
    ctx.setStrokeColor(tickColour)
    for i in 0...12 {
        let a = start + sweep * CGFloat(i) / 12
        let long = i == 0 || i == 6 || i == 12
        ctx.setLineWidth(max(1, size * 0.016))
        ctx.move(to: point(c, r * (long ? 0.86 : 0.89), a))
        ctx.addLine(to: point(c, r * 0.97, a))
        ctx.strokePath()
    }

    // Value arc between the scale and the knob.
    let arcR = r * 0.80, arcW = max(1.5, size * 0.035)
    ctx.setLineWidth(arcW)
    ctx.setStrokeColor(arcTrack)
    ctx.addPath(arcPath(c, arcR, from: start, to: start + sweep))
    ctx.strokePath()
    if value > 0.004 {
        ctx.setStrokeColor(arcValue)
        ctx.addPath(arcPath(c, arcR, from: start, to: angle))
        ctx.strokePath()
    }

    // Knob body with a soft drop shadow, then a slightly lighter cap.
    let bodyR = r * 0.70
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: size * 0.03), blur: size * 0.07, color: rgb(0x000000, 0.75))
    ctx.setFillColor(rgb(0x121315))
    ctx.fillEllipse(in: CGRect(x: c.x - bodyR, y: c.y - bodyR, width: bodyR * 2, height: bodyR * 2))
    ctx.restoreGState()
    radialFill(ctx, centre: c, radius: bodyR, inner: rgb(0x3a3c40), outer: rgb(0x0e0f11), offset: CGPoint(x: -bodyR * 0.3, y: -bodyR * 0.45))

    let capR = bodyR * 0.80
    radialFill(ctx, centre: c, radius: capR, inner: rgb(0x2f3135), outer: rgb(0x17181a), offset: CGPoint(x: -capR * 0.25, y: -capR * 0.5))
    ctx.setLineWidth(max(1, size * 0.012))
    ctx.setStrokeColor(rgb(0x000000, 0.8))
    ctx.strokeEllipse(in: CGRect(x: c.x - capR, y: c.y - capR, width: capR * 2, height: capR * 2))

    // Highlight along the top edge of the body.
    ctx.setLineWidth(max(1, size * 0.014))
    ctx.setStrokeColor(rgb(0xffffff, 0.12))
    ctx.addPath(arcPath(c, bodyR * 0.97, from: -60, to: 60))
    ctx.strokePath()

    // White pointer.
    ctx.setLineCap(.round)
    ctx.setLineWidth(max(1.5, size * 0.04))
    ctx.setStrokeColor(pointerColour)
    ctx.move(to: point(c, bodyR * 0.30, angle))
    ctx.addLine(to: point(c, bodyR * 0.92, angle))
    ctx.strokePath()
}

var rcss = """
/* Generated by tools/gen_art.swift - do not edit by hand. */


"""

// Lays 128 frames out on pages of at most 2048x2048 pixels, the way the TrancyTI sheets are.
func knobSheet(prefix: String, size: Int, cls: String?) {
    let perRow = max(1, 2048 / size)
    let rowsPerPage = max(1, 2048 / size)
    let perPage = perRow * rowsPerPage
    let frames = 128
    var frame = 0
    var page = 0
    while frame < frames {
        let count = min(perPage, frames - frame)
        let rows = (count + perRow - 1) / perRow
        let width = min(count, perRow) * size
        let ctx = makeContext(width, rows * size)
        rcss += "@spritesheet \(prefix)page\(page)\n{\n"
        for i in 0..<count {
            let x = (i % perRow) * size, y = (i / perRow) * size
            drawKnob(ctx, origin: CGPoint(x: x, y: y), size: CGFloat(size), value: CGFloat(frame + i) / CGFloat(frames - 1))
            rcss += "\t\(prefix)\(String(format: "%03d", frame + i)): \(x)px \(y)px \(size)px \(size)px;\n"
        }
        let file = "\(prefix)page\(page).png"
        rcss += "\tsrc: \(file);\n}\n"
        savePNG(ctx, file)
        frame += count
        page += 1
    }
    if let cls {
        rcss += ".\(cls)\n{\n\tframes: \(frames);\n\tspriteprefix: \(prefix);\n}\n"
    }
    rcss += "\n"
}

// MARK: - Buttons

// A state sprite sheet in the same shape as TrancyTI's button_1: default/hover/active and checked variants.
func stateSheet(name: String, width: Int, height: Int, draw: (CGContext, CGPoint, _ lit: Bool, _ pressed: Bool, _ hover: Bool) -> Void) {
    // Rows: 0 off, 1 off+hover, 2 off+pressed, 3 lit, 4 lit+hover, 5 lit+pressed
    let ctx = makeContext(width, height * 6)
    let states: [(Bool, Bool, Bool)] = [(false, false, false), (false, false, true), (false, true, false),
                                        (true, false, false), (true, false, true), (true, true, false)]
    for (row, s) in states.enumerated() {
        draw(ctx, CGPoint(x: 0, y: row * height), s.0, s.1, s.2)
    }
    savePNG(ctx, "\(name).png")
    func rect(_ row: Int) -> String { "0px \(row * height)px \(width)px \(height)px" }
    rcss += """
    @spritesheet \(name)
    {
    \t\(name)_default: \(rect(0));
    \t\(name)_hover: \(rect(1));
    \t\(name)_active: \(rect(2));
    \t\(name)_checked: \(rect(3));
    \t\(name)_checked-hover: \(rect(4));
    \t\(name)_checked-active: \(rect(5));
    \tsrc: \(name).png;
    }

    """
}

// Class rules for a state sheet, positioned with `align` (e.g. "left center").
func stateClasses(cls: String, sheet: String, align: String) {
    for (selector, sprite) in [("", "default"), (":hover", "hover"), (":active", "active"), (":checked", "checked"),
                               (":checked:hover", "checked-hover"), (":checked:active", "checked-active")] {
        rcss += ".\(cls)\(selector)\n{\n\tdecorator: image(\(sheet)_\(sprite) scale-none \(align));\n}\n"
    }
    rcss += "\n"
}

func drawLed(_ ctx: CGContext, centre: CGPoint, radius: CGFloat, lit: Bool) {
    if lit {
        ctx.saveGState()
        ctx.setShadow(offset: .zero, blur: radius * 2.2, color: rgb(0xff2a1a, 0.9))
        ctx.setFillColor(ledOn)
        ctx.fillEllipse(in: CGRect(x: centre.x - radius, y: centre.y - radius, width: radius * 2, height: radius * 2))
        ctx.restoreGState()
        radialFill(ctx, centre: centre, radius: radius, inner: rgb(0xffd2c8), outer: ledOn, offset: CGPoint(x: -radius * 0.3, y: -radius * 0.35))
    } else {
        radialFill(ctx, centre: centre, radius: radius, inner: rgb(0x6a2620), outer: ledOff, offset: CGPoint(x: -radius * 0.3, y: -radius * 0.35))
    }
    ctx.setLineWidth(max(1, radius * 0.18))
    ctx.setStrokeColor(rgb(0x000000, 0.7))
    ctx.strokeEllipse(in: CGRect(x: centre.x - radius, y: centre.y - radius, width: radius * 2, height: radius * 2))
}

func drawKey(_ ctx: CGContext, rect: CGRect, pressed: Bool, hover: Bool) {
    let path = CGPath(roundedRect: rect, cornerWidth: rect.height * 0.12, cornerHeight: rect.height * 0.12, transform: nil)
    ctx.saveGState()
    if !pressed {
        ctx.setShadow(offset: CGSize(width: 0, height: rect.height * 0.06), blur: rect.height * 0.12, color: rgb(0x000000, 0.7))
    }
    ctx.addPath(path)
    ctx.setFillColor(pressed ? rgb(0x1a1b1d) : rgb(0x26282b))
    ctx.fillPath()
    ctx.restoreGState()
    let gradient = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB),
                              colors: [rgb(hover ? 0x4a4d52 : 0x3c3f43), rgb(pressed ? 0x141517 : 0x1d1e21)] as CFArray,
                              locations: [0, 1])!
    ctx.saveGState()
    ctx.addPath(path)
    ctx.clip()
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 0, y: rect.minY), end: CGPoint(x: 0, y: rect.maxY), options: [])
    ctx.restoreGState()
    ctx.addPath(path)
    ctx.setLineWidth(1.5)
    ctx.setStrokeColor(rgb(0x000000, 0.9))
    ctx.strokePath()
}

// LED on its own (for LED + text-label selectors): 30x30 dp.
stateSheet(name: "hwled", width: 30, height: 30) { ctx, o, lit, _, hover in
    drawLed(ctx, centre: CGPoint(x: o.x + 15, y: o.y + 15), radius: hover && !lit ? 9.5 : 9, lit: lit)
}
stateClasses(cls: "hwled", sheet: "hwled", align: "left center")

// Rubber key with an LED above it (toggles and section selects): 88x76 dp.
stateSheet(name: "hwledkey", width: 88, height: 76) { ctx, o, lit, pressed, hover in
    drawLed(ctx, centre: CGPoint(x: o.x + 44, y: o.y + 12), radius: 8, lit: lit)
    drawKey(ctx, rect: CGRect(x: o.x + 6, y: o.y + 28, width: 76, height: 44), pressed: pressed, hover: hover)
}
stateClasses(cls: "hwledkey", sheet: "hwledkey", align: "center top")

// Plain rubber key (EDIT, BROWSE, patch up/down): 88x50 dp.
stateSheet(name: "hwkey", width: 88, height: 50) { ctx, o, _, pressed, hover in
    drawKey(ctx, rect: CGRect(x: o.x + 6, y: o.y + 3, width: 76, height: 44), pressed: pressed, hover: hover)
}
stateClasses(cls: "hwkey", sheet: "hwkey", align: "center top")

// MARK: - Knobs

// Main panel sizes.
knobSheet(prefix: "hwk_l_", size: 168, cls: "hwknobL")
knobSheet(prefix: "hwk_m_", size: 132, cls: "hwknobM")
knobSheet(prefix: "hwk_s_", size: 100, cls: "hwknobS")
// The sizes TrancyTI's edit pages use, so those pages pick up the dark knobs through their own classes.
knobSheet(prefix: "hwk_t70_", size: 70, cls: nil)
knobSheet(prefix: "hwk_t98_", size: 98, cls: nil)
knobSheet(prefix: "hwk_t128_", size: 128, cls: nil)
knobSheet(prefix: "hwk_t223_", size: 223, cls: nil)

try! rcss.write(to: URL(fileURLWithPath: outDir).appendingPathComponent("hw_art.rcss"), atomically: true, encoding: .utf8)
print("wrote artwork and hw_art.rcss to \(outDir)")
