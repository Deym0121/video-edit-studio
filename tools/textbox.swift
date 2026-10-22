// textbox — Apple Vision text lines in still images (Style references: where the captions sit, how big, what case).
// Usage: textbox img1.jpg [img2.jpg …]  →  one JSON line per image: {"file": …, "w": …, "h": …, "lines": [{"t": text, "c": conf, "r": [x, y, w, h]}, …]}
// Rects are in pixels, origin top-left.
// Build: swiftc -O -sdk <MacOSX26.x.sdk> tools/textbox.swift -o tools/bin/textbox
import CoreGraphics
import Foundation
import ImageIO
import Vision

for path in CommandLine.arguments.dropFirst() {
    var lines: [[String: Any]] = []
    var w = 0.0, h = 0.0
    if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
       let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
        w = Double(img.width); h = Double(img.height)
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .accurate
        req.usesLanguageCorrection = false
        if #available(macOS 13.0, *) { req.automaticallyDetectsLanguage = true }
        try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
        for o in req.results ?? [] {
            guard let top = o.topCandidates(1).first, top.confidence > 0.3 else { continue }
            let b = o.boundingBox  // normalized, origin bottom-left
            lines.append(["t": top.string, "c": Double(top.confidence),
                          "r": [Int(b.minX * w), Int((1 - b.maxY) * h), Int(b.width * w), Int(b.height * h)]])
        }
    }
    let line: [String: Any] = ["file": path, "w": Int(w), "h": Int(h), "lines": lines]
    if let d = try? JSONSerialization.data(withJSONObject: line), let s = String(data: d, encoding: .utf8) { print(s) }
}
