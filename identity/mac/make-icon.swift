// Draws the app icon from the mark itself (identity/public/favicon.svg) and writes identity/mac/AppIcon.icns.
// Run it again only if the mark changes; the result is checked in.
//
//     swift identity/mac/make-icon.swift
import AppKit

let root = URL(fileURLWithPath: CommandLine.arguments.first.map { ($0 as NSString).deletingLastPathComponent } ?? ".")
    .appendingPathComponent("..").standardized
guard let mark = NSImage(contentsOf: root.appendingPathComponent("public/favicon.svg")), mark.isValid else {
    print("Couldn't read identity/public/favicon.svg")
    exit(1)
}

func render(size: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let canvas = CGFloat(size)
    let body = canvas * 824 / 1024  // macOS icons leave a margin around the tile
    let inset = (canvas - body) / 2
    // A soft shadow under the tile, as the system's own icons have.
    let shadow = NSShadow()
    shadow.shadowColor = NSColor.black.withAlphaComponent(0.22)
    shadow.shadowBlurRadius = canvas * 0.012
    shadow.shadowOffset = NSSize(width: 0, height: -canvas * 0.006)
    shadow.set()
    mark.draw(in: NSRect(x: inset, y: inset, width: body, height: body))
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}

let iconset = root.appendingPathComponent("mac/AppIcon.iconset", isDirectory: true)
try? FileManager.default.removeItem(at: iconset)
try FileManager.default.createDirectory(at: iconset, withIntermediateDirectories: true)
for (name, size) in [("16x16", 16), ("16x16@2x", 32), ("32x32", 32), ("32x32@2x", 64), ("128x128", 128), ("128x128@2x", 256),
                     ("256x256", 256), ("256x256@2x", 512), ("512x512", 512), ("512x512@2x", 1024)] {
    try render(size: size).write(to: iconset.appendingPathComponent("icon_\(name).png"))
}
let task = Process()
task.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
task.arguments = ["-c", "icns", iconset.path, "-o", root.appendingPathComponent("mac/AppIcon.icns").path]
try task.run()
task.waitUntilExit()
try? FileManager.default.removeItem(at: iconset)
print(task.terminationStatus == 0 ? "Wrote identity/mac/AppIcon.icns" : "iconutil failed")
