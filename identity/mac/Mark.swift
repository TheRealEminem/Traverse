import AppKit

/// The menu bar icon: the app's mark as line art (a low sun, and a trail crossing a slope to a small cairn).
/// It matches the app icon and the logo in the sidebar (identity/art.tsx).
enum Mark {
    static let menuIcon = icon(dimmed: false)
    static let menuIconDimmed = icon(dimmed: true)

    private static func icon(dimmed: Bool) -> NSImage {
        let image = NSImage(size: NSSize(width: 18, height: 18), flipped: false) { _ in
            NSColor.black.setStroke()
            NSColor.black.setFill()
            NSBezierPath(ovalIn: NSRect(x: 1.6, y: 11.8, width: 4.6, height: 4.6)).fill()  // sun

            let trail = NSBezierPath()  // the trail across the slope
            trail.move(to: NSPoint(x: 1.8, y: 2.2))
            trail.curve(to: NSPoint(x: 10.2, y: 6.2), controlPoint1: NSPoint(x: 4.6, y: 3.4), controlPoint2: NSPoint(x: 7.4, y: 4.8))
            trail.lineWidth = 1.9
            trail.lineCapStyle = .round
            trail.stroke()

            // the cairn: three stones, filled so they stay legible at this size
            NSBezierPath(ovalIn: NSRect(x: 11.2, y: 4.9, width: 5.6, height: 2.8)).fill()
            NSBezierPath(ovalIn: NSRect(x: 12.0, y: 8.3, width: 4.0, height: 2.3)).fill()
            NSBezierPath(ovalIn: NSRect(x: 12.7, y: 11.2, width: 2.6, height: 1.8)).fill()
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
