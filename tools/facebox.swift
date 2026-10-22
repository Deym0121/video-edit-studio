// facebox — Apple Vision face rectangles for still images (Edit Health: "does a graphic cover the face?").
// Usage: facebox img1.png [img2.png …]  →  one JSON line per image: {"file": …, "faces": [[x, y, w, h], …]}
// Rects are in pixels, origin top-left (like the 1080×1920 frame the graphics are designed on).
// Build: swiftc -O -sdk <MacOSX26.x.sdk> tools/facebox.swift -o tools/bin/facebox
import CoreGraphics
import Foundation
import ImageIO
import Vision

for path in CommandLine.arguments.dropFirst() {
    var faces: [[Int]] = []
    if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
       let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
        let w = Double(img.width), h = Double(img.height)
        let req = VNDetectFaceRectanglesRequest()
        try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
        for f in req.results ?? [] where f.confidence > 0.5 {
            let b = f.boundingBox  // normalized, origin bottom-left
            faces.append([Int(b.minX * w), Int((1 - b.maxY) * h), Int(b.width * w), Int(b.height * h)])
        }
    }
    let line: [String: Any] = ["file": path, "faces": faces]
    if let d = try? JSONSerialization.data(withJSONObject: line), let s = String(data: d, encoding: .utf8) { print(s) }
}
