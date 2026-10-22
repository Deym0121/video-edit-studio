// tosdr — iPhone HDR (HLG + Dolby Vision) → SDR Rec.709 with Apple's own tone mapping, the same
// conversion Photos / iMovie use for "Most Compatible". The footage then looks the way the camera
// shows it, on every phone and app (an 8-bit HLG render without the Dolby Vision data plays as "HDR").
//
//   tosdr <in> <out.mov> [--range <start> <dur>] [--comp]   video only, ProRes 422 HQ, original frame timing
//   tosdr --frame <in> <seconds> <out.png>                   one SDR still (reference for colour checks)
//
// build: swiftc -O tools/tosdr.swift -o tools/bin/tosdr
import AVFoundation
import CoreImage
import ImageIO
import UniformTypeIdentifiers

func fail(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }

var a = Array(CommandLine.arguments.dropFirst())
let sdr: [String: Any] = [AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
                          AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
                          AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2]

if a.first == "--frame" {
    guard a.count == 4, let s = Double(a[2]) else { fail("usage: tosdr --frame <in> <seconds> <out.png>") }
    let g = AVAssetImageGenerator(asset: AVURLAsset(url: URL(fileURLWithPath: a[1])))
    g.requestedTimeToleranceBefore = .zero
    g.requestedTimeToleranceAfter = .zero
    g.appliesPreferredTrackTransform = true
    let img: CGImage
    do { img = try g.copyCGImage(at: CMTime(seconds: s, preferredTimescale: 600), actualTime: nil) } catch { fail("frame: \(error)") }
    guard let d = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[3]) as CFURL, UTType.png.identifier as CFString, 1, nil) else { fail("png") }
    CGImageDestinationAddImage(d, img, nil)
    exit(CGImageDestinationFinalize(d) ? 0 : 1)
}

var range: CMTimeRange? = nil
if let i = a.firstIndex(of: "--range"), i + 2 < a.count, let s = Double(a[i + 1]), let d = Double(a[i + 2]) {
    range = CMTimeRange(start: CMTime(seconds: s, preferredTimescale: 600), duration: CMTime(seconds: d, preferredTimescale: 600))
    a.removeSubrange(i...(i + 2))
}
let comp = a.contains("--comp")
a.removeAll { $0 == "--comp" }
guard a.count == 2 else { fail("usage: tosdr <in> <out.mov> [--range <start> <dur>] [--comp]") }

let asset = AVURLAsset(url: URL(fileURLWithPath: a[0]))
guard let track = asset.tracks(withMediaType: .video).first else { fail("no video track") }
let size = track.naturalSize
let px: [String: Any] = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_422YpCbCr10BiPlanarVideoRange]

let reader: AVAssetReader
do { reader = try AVAssetReader(asset: asset) } catch { fail("reader: \(error)") }
if let r = range { reader.timeRange = r }
let output: AVAssetReaderOutput
if comp {  // AVVideoComposition with SDR colour properties = the WWDC20 "HDR → SDR" path
    let vc = AVMutableVideoComposition(propertiesOf: asset)
    vc.colorPrimaries = AVVideoColorPrimaries_ITU_R_709_2
    vc.colorTransferFunction = AVVideoTransferFunction_ITU_R_709_2
    vc.colorYCbCrMatrix = AVVideoYCbCrMatrix_ITU_R_709_2
    let o = AVAssetReaderVideoCompositionOutput(videoTracks: [track], videoSettings: px)
    o.videoComposition = vc
    output = o
} else {   // decode + colour conversion to Rec.709 per frame, keeping each frame's own timestamp
    var s = px
    s[AVVideoColorPropertiesKey] = sdr
    output = AVAssetReaderTrackOutput(track: track, outputSettings: s)
}
output.alwaysCopiesSampleData = false
reader.add(output)

let url = URL(fileURLWithPath: a[1])
try? FileManager.default.removeItem(at: url)
let writer: AVAssetWriter
do { writer = try AVAssetWriter(outputURL: url, fileType: .mov) } catch { fail("writer: \(error)") }
let vin = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.proRes422HQ, AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
    AVVideoColorPropertiesKey: sdr])
vin.expectsMediaDataInRealTime = false
vin.transform = track.preferredTransform
writer.add(vin)

guard reader.startReading() else { fail("read: \(String(describing: reader.error))") }
guard writer.startWriting() else { fail("write: \(String(describing: writer.error))") }
var n = 0
while let sb = output.copyNextSampleBuffer() {
    let pts = CMSampleBufferGetPresentationTimeStamp(sb)
    if n == 0 { writer.startSession(atSourceTime: pts); print("first pts \(pts.seconds)") }
    while !vin.isReadyForMoreMediaData { usleep(500) }
    guard vin.append(sb) else { fail("append: \(String(describing: writer.error))") }
    n += 1
    if n % 1500 == 0 { print("\(n) frames"); fflush(stdout) }
}
if reader.status == .failed { fail("read: \(String(describing: reader.error))") }
vin.markAsFinished()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
if writer.status != .completed { fail("finish: \(String(describing: writer.error))") }
print("frames \(n)")
