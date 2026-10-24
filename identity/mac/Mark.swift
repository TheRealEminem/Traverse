import AppKit

/// The menu bar icon: the app's mark as a silhouette (a low sun, and a cairn of balanced stones).
/// It matches the app icon and the logo in the sidebar (identity/art.tsx).
enum Mark {
    static let menuIcon = icon(dimmed: false)
    static let menuIconDimmed = icon(dimmed: true)

    private static func icon(dimmed: Bool) -> NSImage {
        let image = NSImage(size: NSSize(width: 18, height: 18), flipped: false) { _ in
            NSColor.black.setStroke()
            NSColor.black.setFill()
            NSBezierPath(ovalIn: NSRect(x: 12.2, y: 11.4, width: 4.6, height: 4.6)).fill()  // sun

            // the cairn: six stones, flat slabs of uneven width, each turned a little, as on the mark
            let stones: [(x: CGFloat, y: CGFloat, w: CGFloat, h: CGFloat, tilt: CGFloat)] = [
                (x: 8.00, y: 3.10, w: 9.14, h: 3.07, tilt: 2),
                (x: 8.29, y: 5.51, w: 7.90, h: 2.19, tilt: -3),
                (x: 7.85, y: 7.78, w: 5.56, h: 2.63, tilt: 6),
                (x: 8.44, y: 10.12, w: 6.87, h: 2.05, tilt: -5),
                (x: 8.15, y: 12.31, w: 3.66, h: 2.19, tilt: 3),
                (x: 8.33, y: 14.14, w: 2.05, h: 1.39, tilt: -8),
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
