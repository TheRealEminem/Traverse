import AppKit

/// The menu bar icon: the app's mark as a silhouette (a low sun, and a cairn of four flat stones).
/// It matches the app icon and the logo in the sidebar (identity/art.tsx).
enum Mark {
    static let menuIcon = icon(dimmed: false)
    static let menuIconDimmed = icon(dimmed: true)

    private static func icon(dimmed: Bool) -> NSImage {
        let image = NSImage(size: NSSize(width: 18, height: 18), flipped: false) { _ in
            NSColor.black.setStroke()
            NSColor.black.setFill()
            NSBezierPath(ovalIn: NSRect(x: 12.6, y: 12.2, width: 4.6, height: 4.6)).fill()  // sun

            // the cairn: four flat stones, widest at the bottom, each turned a little, as on the mark
            let stones: [(x: CGFloat, y: CGFloat, w: CGFloat, h: CGFloat, tilt: CGFloat)] = [
                (x: 8.05, y: 3.40, w: 12.4, h: 3.6, tilt: 0),
                (x: 8.60, y: 7.50, w: 8.8, h: 3.0, tilt: 4),
                (x: 8.10, y: 11.10, w: 6.6, h: 2.6, tilt: -5),
                (x: 8.55, y: 14.30, w: 4.2, h: 2.2, tilt: 7),
            ]
            for s in stones {
                let stone = NSBezierPath(ovalIn: NSRect(x: -s.w / 2, y: -s.h / 2, width: s.w, height: s.h))
                var at = AffineTransform(translationByX: s.x, byY: s.y)
                at.rotate(byDegrees: s.tilt)
                stone.transform(using: at)
                stone.fill()
            }
            return true
        }
        image.isTemplate = true
        guard dimmed else { return image }
        let faded = NSImage(size: image.size, flipped: false) { rect in
            image.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 0.45)
            return true
        }
        faded.isTemplate = true
        return faded
    }
}
