// The Lodge's palette for native (SwiftUI) parts of a family app: menu bar extras, native panels, widgets.
// Same values as tokens.css (Day = light, Dusk = dark). Generated from core/web/index.css on 2026-10-13.
// Use: .tint(Brand.forest), Text("…").foregroundStyle(Brand.inkSoft). The system font (SF) is used natively.
import SwiftUI

enum Brand {
    static let canvas        = Color(light: 0xF7F4EC, dark: 0x0E1416)
    static let surface       = Color(light: 0xFFFDF8, dark: 0x172023)
    static let surfaceSubtle = Color(light: 0xF2EEE4, dark: 0x131B1D)
    static let ink           = Color(light: 0x21271F, dark: 0xECEAE3)
    static let inkSoft       = Color(light: 0x666A5F, dark: 0xA9AAA1)
    static let inkFaint      = Color(light: 0x979A8F, dark: 0x72776F)
    static let forest        = Color(light: 0x1F5E4B, dark: 0x52A487)
    static let forestSoft    = Color(light: 0xD9E8E0, dark: 0x19332F)
    static let forestDeep    = Color(light: 0x174838, dark: 0x96D5BE)
    static let trail         = Color(light: 0xDE5F31, dark: 0xEC7347)
    static let trailSoft     = Color(light: 0xFADFD2, dark: 0x3A2219)
    static let trailDeep     = Color(light: 0x9E3A16, dark: 0xF4A784)
    static let sun           = Color(light: 0xF2B13C, dark: 0xF3B955)
    static let sunSoft       = Color(light: 0xFBECCB, dark: 0x352B16)
    static let sunDeep       = Color(light: 0x764C06, dark: 0xF3D08C)
    static let sky           = Color(light: 0x457F9C, dark: 0x7DB3CF)
    static let skySoft       = Color(light: 0xDFECF1, dark: 0x172A34)
    static let skyDeep       = Color(light: 0x22566E, dark: 0xA8D0E4)
    static let berry         = Color(light: 0x9A4F6B, dark: 0xCC85A0)
    static let berrySoft     = Color(light: 0xF3E2E8, dark: 0x321F28)
    static let berryDeep     = Color(light: 0x76304D, dark: 0xE5B0C4)
    static let onAccent      = Color(light: 0xFFFFFF, dark: 0x0C1214)
}

extension Color {
    /// A color that follows the system appearance: `light` in Day, `dark` in Dusk.
    init(light: UInt32, dark: UInt32) {
        self.init(nsColor: NSColor(name: nil) { appearance in
            let hex = appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? dark : light
            return NSColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255,
                           green: CGFloat((hex >> 8) & 0xFF) / 255,
                           blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
        })
    }
}
