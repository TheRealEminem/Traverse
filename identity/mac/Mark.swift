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

            // the cairn: five stones, filled so they stay legible at this size
            for (x, y, w, h) in [(3.6, 1.8, 8.8, 3.2), (4.5, 4.4, 7.0, 2.8), (5.3, 6.9, 5.2, 2.4), (6.0, 9.2, 3.8, 2.0), (6.5, 11.2, 2.8, 1.6)] {
                NSBezierPath(ovalIn: NSRect(x: x, y: y, width: w, height: h)).fill()
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
