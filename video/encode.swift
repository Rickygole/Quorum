import AVFoundation
import Foundation
import CoreGraphics
import ImageIO

func fail(_ m: String) -> Never { FileHandle.standardError.write((m + "\n").data(using: .utf8)!); exit(1) }

let args = CommandLine.arguments
guard args.count >= 4 else { fail("usage: encode <framesDir> <audio.wav> <out.mp4> [fps]") }
let framesDir = args[1], audioPath = args[2], outPath = args[3]
let fps = args.count > 4 ? Int32(args[4]) ?? 30 : 30

let fm = FileManager.default
let frames = try! fm.contentsOfDirectory(atPath: framesDir)
    .filter { $0.hasPrefix("frame_") && $0.hasSuffix(".png") }.sorted()
guard !frames.isEmpty else { fail("no frames in \(framesDir)") }

guard let probe = CGImageSourceCreateWithURL(URL(fileURLWithPath: framesDir + "/" + frames[0]) as CFURL, nil),
      let first = CGImageSourceCreateImageAtIndex(probe, 0, nil) else { fail("cannot read first frame") }
let W = first.width, H = first.height

let outURL = URL(fileURLWithPath: outPath)
try? fm.removeItem(at: outURL)
let writer = try! AVAssetWriter(outputURL: outURL, fileType: .mp4)

let videoSettings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: W, AVVideoHeightKey: H,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 12_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: fps * 2,
        AVVideoAllowFrameReorderingKey: true,
    ],
]
let vin = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
vin.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: vin, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA),
    kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
])
writer.add(vin)

let audioURL = URL(fileURLWithPath: audioPath)
let audioAsset = AVURLAsset(url: audioURL)
var ain: AVAssetWriterInput? = nil
var areader: AVAssetReader? = nil
var aout: AVAssetReaderTrackOutput? = nil
if let track = audioAsset.tracks(withMediaType: .audio).first {
    var layout = AudioChannelLayout()
    memset(&layout, 0, MemoryLayout<AudioChannelLayout>.size)
    layout.mChannelLayoutTag = kAudioChannelLayoutTag_Mono
    let layoutData = Data(bytes: &layout, count: MemoryLayout<AudioChannelLayout>.size)
    let settings: [String: Any] = [
        AVFormatIDKey: kAudioFormatMPEG4AAC,
        AVSampleRateKey: 44100,
        AVNumberOfChannelsKey: 1,
        AVEncoderBitRateKey: 128_000,
        AVChannelLayoutKey: layoutData,
    ]
    let i = AVAssetWriterInput(mediaType: .audio, outputSettings: settings)
    i.expectsMediaDataInRealTime = false
    writer.add(i); ain = i
    let r = try! AVAssetReader(asset: audioAsset)
    let o = AVAssetReaderTrackOutput(track: track, outputSettings: [
        AVFormatIDKey: kAudioFormatLinearPCM,
        AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false,
        AVLinearPCMIsBigEndianKey: false, AVLinearPCMIsNonInterleaved: false,
    ])
    r.add(o); r.startReading(); areader = r; aout = o
}

writer.startWriting()
writer.startSession(atSourceTime: .zero)

let cs = CGColorSpaceCreateDeviceRGB()
var pool: CVPixelBufferPool?
CVPixelBufferPoolCreate(nil, nil, [
    kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA),
    kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
] as CFDictionary, &pool)

let vq = DispatchQueue(label: "video")
let group = DispatchGroup()

group.enter()
vin.requestMediaDataWhenReady(on: vq) {
    var idx = 0
    while vin.isReadyForMoreMediaData {
        if idx >= frames.count { vin.markAsFinished(); group.leave(); return }
        let path = framesDir + "/" + frames[idx]
        guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
              let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { idx += 1; continue }
        var pb: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, pool!, &pb)
        guard let buf = pb else { idx += 1; continue }
        CVPixelBufferLockBaseAddress(buf, [])
        if let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buf), width: W, height: H,
                               bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buf),
                               space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue) {
            ctx.draw(img, in: CGRect(x: 0, y: 0, width: W, height: H))
        }
        CVPixelBufferUnlockBaseAddress(buf, [])
        adaptor.append(buf, withPresentationTime: CMTime(value: CMTimeValue(idx), timescale: fps))
        idx += 1
        if idx % 300 == 0 { FileHandle.standardError.write("  encoded \(idx)/\(frames.count)\n".data(using: .utf8)!) }
    }
}

if let ain = ain, let areader = areader, let aout = aout {
    group.enter()
    ain.requestMediaDataWhenReady(on: DispatchQueue(label: "audio")) {
        while ain.isReadyForMoreMediaData {
            if areader.status == .reading, let sb = aout.copyNextSampleBuffer() {
                ain.append(sb)
            } else {
                ain.markAsFinished(); group.leave(); return
            }
        }
    }
}

group.wait()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()

if writer.status == .completed {
    let attrs = try! fm.attributesOfItem(atPath: outPath)
    let mb = Double(attrs[.size] as! Int) / 1_048_576
    let secs = Double(frames.count) / Double(fps)
    print(String(format: "wrote %@  %dx%d  %d frames  %.1fs  %.1f MB", outPath, W, H, frames.count, secs, mb))
} else {
    fail("encode failed: \(String(describing: writer.error))")
}
