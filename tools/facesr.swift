// facesr W H [SCALE] — Apple low-latency super-resolution (VideoToolbox VTFrameProcessor, macOS 26) on raw NV12 frames.
// stdin: W×H nv12 frames (video range) · stdout: (W·S)×(H·S) nv12 frames. Built for the tiny Zoom speaker tile in
// webinar recordings (tools/zoomclip.py). Build: swiftc -O -sdk <MacOSX26.x.sdk> tools/facesr.swift -o tools/bin/facesr
import CoreVideo
import Foundation
import VideoToolbox

let args = CommandLine.arguments
guard args.count >= 3, let w = Int(args[1]), let h = Int(args[2]) else {
    FileHandle.standardError.write("usage: facesr W H [SCALE]\n".data(using: .utf8)!); exit(2)
}
let scale = Float(args.count > 3 ? args[3] : "4") ?? 4
guard VTLowLatencySuperResolutionScalerConfiguration.isSupported,
      VTLowLatencySuperResolutionScalerConfiguration.supportedScaleFactors(frameWidth: w, frameHeight: h).contains(scale) else {
    FileHandle.standardError.write("facesr: \(w)x\(h) ×\(scale) not supported\n".data(using: .utf8)!); exit(3)
}
let cfg = VTLowLatencySuperResolutionScalerConfiguration(frameWidth: w, frameHeight: h, scaleFactor: scale)
let ow = Int(Float(w) * scale), oh = Int(Float(h) * scale)
let proc = VTFrameProcessor()
do { try proc.startSession(configuration: cfg) } catch {
    FileHandle.standardError.write("facesr: session failed: \(error)\n".data(using: .utf8)!); exit(4)
}

func makeBuffer(_ attrs: [String: Any], _ bw: Int, _ bh: Int) -> CVPixelBuffer {
    var pb: CVPixelBuffer?
    CVPixelBufferCreate(nil, bw, bh, kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange, attrs as CFDictionary, &pb)
    return pb!
}

let inSize = w * h * 3 / 2, outSize = ow * oh * 3 / 2
let stdin = FileHandle.standardInput, stdout = FileHandle.standardOutput
var n: Int64 = 0
var out = Data(count: outSize)
while true {
    var chunk = Data()
    while chunk.count < inSize {
        let d = stdin.readData(ofLength: inSize - chunk.count)
        if d.isEmpty { break }
        chunk.append(d)
    }
    if chunk.count < inSize { break }
    let src = makeBuffer(cfg.sourcePixelBufferAttributes, w, h)
    let dst = makeBuffer(cfg.destinationPixelBufferAttributes, ow, oh)
    CVPixelBufferLockBaseAddress(src, [])
    chunk.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
        for (plane, rows, off) in [(0, h, 0), (1, h / 2, w * h)] {
            let base = CVPixelBufferGetBaseAddressOfPlane(src, plane)!, bpr = CVPixelBufferGetBytesPerRowOfPlane(src, plane)
            for r in 0..<rows { memcpy(base + r * bpr, raw.baseAddress! + off + r * w, w) }
        }
    }
    CVPixelBufferUnlockBaseAddress(src, [])
    let t = CMTime(value: n, timescale: 30)
    guard let sf = VTFrameProcessorFrame(buffer: src, presentationTimeStamp: t),
          let df = VTFrameProcessorFrame(buffer: dst, presentationTimeStamp: t) else { exit(5) }
    let params = VTLowLatencySuperResolutionScalerParameters(sourceFrame: sf, destinationFrame: df)
    let sem = DispatchSemaphore(value: 0)
    var failed: Error?
    proc.process(parameters: params) { _, err in failed = err; sem.signal() }
    sem.wait()
    if let e = failed { FileHandle.standardError.write("facesr: frame \(n): \(e)\n".data(using: .utf8)!); exit(6) }
    CVPixelBufferLockBaseAddress(dst, .readOnly)
    out.withUnsafeMutableBytes { (raw: UnsafeMutableRawBufferPointer) in
        for (plane, rows, off) in [(0, oh, 0), (1, oh / 2, ow * oh)] {
            let base = CVPixelBufferGetBaseAddressOfPlane(dst, plane)!, bpr = CVPixelBufferGetBytesPerRowOfPlane(dst, plane)
            for r in 0..<rows { memcpy(raw.baseAddress! + off + r * ow, base + r * bpr, ow) }
        }
    }
    CVPixelBufferUnlockBaseAddress(dst, .readOnly)
    stdout.write(out)
    n += 1
}
proc.endSession()
