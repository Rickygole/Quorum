import AVFoundation

let args = CommandLine.arguments
guard args.count >= 4, let rate = Float(args[3]) else {
    print("usage: tempo <in> <out.wav> <rate>")
    exit(1)
}
let inFile = try AVAudioFile(forReading: URL(fileURLWithPath: args[1]))
let format = inFile.processingFormat
let engine = AVAudioEngine()
let player = AVAudioPlayerNode()
let stretch = AVAudioUnitTimePitch()
stretch.rate = rate
stretch.overlap = 16
engine.attach(player)
engine.attach(stretch)
engine.connect(player, to: stretch, format: format)
engine.connect(stretch, to: engine.mainMixerNode, format: format)
try engine.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 4096)
try engine.start()
player.scheduleFile(inFile, at: nil)
player.play()
let outSettings: [String: Any] = [
    AVFormatIDKey: kAudioFormatLinearPCM,
    AVSampleRateKey: format.sampleRate,
    AVNumberOfChannelsKey: format.channelCount,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
]
let outFile = try AVAudioFile(forWriting: URL(fileURLWithPath: args[2]), settings: outSettings)
let buffer = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: engine.manualRenderingMaximumFrameCount)!
let target = AVAudioFramePosition(Double(inFile.length) / Double(rate)) + 8192
while engine.manualRenderingSampleTime < target {
    let n = min(buffer.frameCapacity, AVAudioFrameCount(target - engine.manualRenderingSampleTime))
    let status = try engine.renderOffline(n, to: buffer)
    if status == .success { try outFile.write(from: buffer) } else if status == .error { break }
}
player.stop()
engine.stop()
outFile.close()
print("wrote \(args[2])")
