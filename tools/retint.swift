// Turns TrancyTI's light-grey edit page artwork into dark panels with light print, so the edit
// pages match the charcoal front panel.
//
//     retint <strength 0-1> <file.png>...
//
// Wherever the panel *behind* a pixel is light, the panel goes dark. Thin dark print on it
// (labels, scales, grille dots) is inverted to light; broad dark areas (knob holes, drop
// shadows) stay dark, so they don't turn into glowing halos. Areas that were already dark keep
// their look. Coloured accents (red text, blue LEDs) keep their colour.

import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count > 2, let strength = Double(args[1]) else {
    print("usage: retint <strength 0-1> <file.png>...")
    exit(1)
}

let panelRadius = 14 // how far around a pixel to look for the panel behind it
let strokeRadius = 4 // print thinner than about twice this counts as "thin"
let coreRadius = 8 // a dark area that fills a box this size is a hole or shadow, never print

// Inverted brightness, compressed so a light panel lands on charcoal and print on off-white.
func invert(_ l: Double) -> Double { 0.95 - l * 0.8 }

/// Summed-area table over a w×h grid, for fast box sums.
struct BoxSum {
    let w: Int, h: Int
    var table: [Double]
    init(_ values: [Double], _ w: Int, _ h: Int) {
        self.w = w; self.h = h
        table = [Double](repeating: 0, count: (w + 1) * (h + 1))
        for y in 0..<h {
            var row = 0.0
            for x in 0..<w {
                row += values[y * w + x]
                table[(y + 1) * (w + 1) + x + 1] = table[y * (w + 1) + x + 1] + row
            }
        }
    }
    func sum(_ x: Int, _ y: Int, _ r: Int) -> Double {
        let x0 = max(0, x - r), x1 = min(w, x + r + 1)
        let y0 = max(0, y - r), y1 = min(h, y + r + 1)
        return table[y1 * (w + 1) + x1] - table[y0 * (w + 1) + x1] - table[y1 * (w + 1) + x0] + table[y0 * (w + 1) + x0]
    }
    func mean(_ x: Int, _ y: Int, _ r: Int) -> Double {
        let x0 = max(0, x - r), x1 = min(w, x + r + 1)
        let y0 = max(0, y - r), y1 = min(h, y + r + 1)
        return sum(x, y, r) / Double((x1 - x0) * (y1 - y0))
    }
}

for path in args.dropFirst(2) {
    let url = URL(fileURLWithPath: path) as CFURL
    guard let source = CGImageSourceCreateWithURL(url, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { continue }
    let w = image.width, h = image.height
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
    let px = ctx.data!.bindMemory(to: UInt8.self, capacity: w * h * 4)

    // Lightness of each pixel as seen on the dark overlay frame (premultiplied = over black).
    var light = [Double](repeating: 0, count: w * h)
    for i in 0..<(w * h) {
        let p = i * 4
        light[i] = (0.299 * Double(px[p]) + 0.587 * Double(px[p + 1]) + 0.114 * Double(px[p + 2])) / 255
    }
    let all = BoxSum(light, w, h)

    // The panel behind a pixel: the local average of only the pixels close to the overall local
    // average, so neither dark print on a light panel nor white print on a dark strip counts.
    var mask = [Double](repeating: 0, count: w * h), masked = mask
    for y in 0..<h {
        for x in 0..<w where abs(light[y * w + x] - all.mean(x, y, panelRadius)) < 0.18 {
            mask[y * w + x] = 1
            masked[y * w + x] = light[y * w + x]
        }
    }
    let maskSum = BoxSum(mask, w, h), maskedSum = BoxSum(masked, w, h)

    // Cores of broad dark areas: dark across a box bigger than any letter.
    // Their edges look like thin print too, so anything near a core counts as broad.
    var core = [Double](repeating: 0, count: w * h)
    for y in 0..<h {
        for x in 0..<w where all.mean(x, y, coreRadius) < 0.25 {
            core[y * w + x] = 1
        }
    }
    let coreSum = BoxSum(core, w, h)

    for y in 0..<h {
        for x in 0..<w {
            let p = (y * w + x) * 4
            let a = Double(px[p + 3])
            if a == 0 { continue }
            var r = Double(px[p]) / a, g = Double(px[p + 1]) / a, b = Double(px[p + 2]) / a
            if max(r, g, b) - min(r, g, b) > 0.12 { continue } // coloured accent: keep

            let n = maskSum.sum(x, y, panelRadius)
            let panel = n > 0 ? maskedSum.sum(x, y, panelRadius) / n : light[y * w + x]
            // How light the panel is (0 = already dark, keep; 1 = light panel, turn dark).
            let onLight = min(1, max(0, (panel - 0.40) / 0.08)) * strength
            if onLight == 0 { continue }
            let l = 0.299 * r + 0.587 * g + 0.114 * b

            // Thin print is darker than its close surroundings; a broad dark area is not.
            var thin = min(1, max(0, (all.mean(x, y, strokeRadius) - l) / 0.12))
            if coreSum.sum(x, y, coreRadius + 3) > 0 { thin = 0 }
            // Broad areas keep their shading relative to the panel, scaled onto its dark tone.
            let shaded = invert(panel) * min(1.2, l / max(panel, 0.01))
            let target = thin * invert(l) + (1 - thin) * shaded
            let mixed = l + (target - l) * onLight
            r = mixed * 0.98; g = mixed; b = mixed * 1.03
            px[p] = UInt8(min(255, max(0, r * a)))
            px[p + 1] = UInt8(min(255, max(0, g * a)))
            px[p + 2] = UInt8(min(255, max(0, b * a)))
        }
    }

    let dest = CGImageDestinationCreateWithURL(url, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
}
