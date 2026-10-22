// personmask — Apple Vision person segmentation for the "text behind the speaker" effect.
// Usage: ffmpeg … -f rawvideo -pix_fmt bgra - | personmask <w> <h> > masks.gray
// Reads raw BGRA frames (w*h*4 bytes) on stdin, writes one 8-bit grey mask per frame
// (w*h bytes, 255 = person) on stdout. Frame-exact because ffmpeg does the decoding/trimming.
// Build: swiftc -O -sdk <MacOSX26.x.sdk> tools/personmask.swift -o tools/bin/personmask
import CoreImage
import CoreVideo
import Foundation
import Vision

let a = CommandLine.arguments
guard a.count == 3, let w = Int(a[1]), let h = Int(a[2]) else {
    FileHandle.standardError.write("usage: personmask <w> <h>\n".data(using: .utf8)!)
    exit(2)
}
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let seq = VNSequenceRequestHandler()
let ctx = CIContext(options: [.workingColorSpace: NSNull()])
let stdin = FileHandle.standardInput, stdout = FileHandle.standardOutput
let frameBytes = w * h * 4
var mask = [UInt8](repeating: 0, count: w * h)

func readFrame() -> Data? {
    var d = Data(capacity: frameBytes)
    while d.count < frameBytes {
        let chunk = stdin.readData(ofLength: frameBytes - d.count)
        if chunk.isEmpty { return nil }
        d.append(chunk)
    }
    return d
}

while let frame = readFrame() {
    autoreleasepool {
        var px: CVPixelBuffer?
        CVPixelBufferCreate(nil, w, h, kCVPixelFormatType_32BGRA, nil, &px)
        guard let pb = px else { return }
        CVPixelBufferLockBaseAddress(pb, [])
        let dst = CVPixelBufferGetBaseAddress(pb)!, rb = CVPixelBufferGetBytesPerRow(pb)
        frame.withUnsafeBytes { src in
            for y in 0..<h { memcpy(dst + y * rb, src.baseAddress! + y * w * 4, w * 4) }
        }
        CVPixelBufferUnlockBaseAddress(pb, [])
        mask = [UInt8](repeating: 0, count: w * h)
        if (try? seq.perform([req], on: pb)) != nil, let m = req.results?.first?.pixelBuffer {
            let im = CIImage(cvPixelBuffer: m)
            let scaled = im.transformed(by: CGAffineTransform(scaleX: CGFloat(w) / im.extent.width,
                                                              y: CGFloat(h) / im.extent.height))
            mask.withUnsafeMutableBytes { p in
                ctx.render(scaled, toBitmap: p.baseAddress!, rowBytes: w,
                           bounds: CGRect(x: 0, y: 0, width: w, height: h), format: .L8, colorSpace: nil)
            }
        }
        stdout.write(Data(mask))
    }
}
