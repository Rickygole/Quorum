import WebKit
import AppKit
import Foundation

struct Step: Decodable {
    let seekFrom: Double?
    let seekTo: Double?
    let fps: Double?
    let js: String?
    let settle: Double?
    let frames: Int?
    let scrollFrom: Double?
    let scrollTo: Double?
}

let a = CommandLine.arguments
guard a.count >= 4 else {
    FileHandle.standardError.write("usage: capture <url> <script.json> <outDir> [w] [h] [startIndex]\n".data(using: .utf8)!)
    exit(2)
}
let urlStr = a[1], scriptPath = a[2], outDir = a[3]
let W = a.count > 4 ? Int(a[4]) ?? 1920 : 1920
let H = a.count > 5 ? Int(a[5]) ?? 1080 : 1080
var frameIndex = a.count > 6 ? Int(a[6]) ?? 0 : 0

let steps = try! JSONDecoder().decode([Step].self, from: Data(contentsOf: URL(fileURLWithPath: scriptPath)))
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: W, height: H), styleMask: [.borderless], backing: .buffered, defer: false)
win.isReleasedWhenClosed = false
let view = WKWebView(frame: NSRect(x: 0, y: 0, width: W, height: H), configuration: WKWebViewConfiguration())
win.contentView = view
win.orderFrontRegardless()
win.setFrameOrigin(NSPoint(x: -20000, y: -20000))
view.load(URLRequest(url: URL(string: urlStr)!))

func sleepRunLoop(_ s: Double) {
    let end = Date(timeIntervalSinceNow: s)
    while Date() < end { RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.01)) }
}

func evalJS(_ js: String) {
    var done = false
    view.evaluateJavaScript(js) { _, e in
        if let e = e { FileHandle.standardError.write("  js error: \(e)\n".data(using: .utf8)!) }
        done = true
    }
    while !done { RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.01)) }
}

func snap(_ path: String) {
    var done = false
    let cfg = WKSnapshotConfiguration()
    cfg.rect = CGRect(x: 0, y: 0, width: W, height: H)
    view.takeSnapshot(with: cfg) { image, _ in
        if let image = image, let tiff = image.tiffRepresentation,
           let rep = NSBitmapImageRep(data: tiff),
           let png = rep.representation(using: .png, properties: [:]) {
            try? png.write(to: URL(fileURLWithPath: path))
        }
        done = true
    }
    while !done { RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.01)) }
}

sleepRunLoop(9.0)
evalJS("""
var s=document.createElement('style');
s.textContent='*{animation:none !important;transition:none !important}';
document.head.appendChild(s);
document.querySelectorAll('[style*="opacity"]').forEach(function(e){e.style.opacity=1});
""")
sleepRunLoop(1.0)

for (n, step) in steps.enumerated() {
    if let js = step.js { evalJS(js) }
    sleepRunLoop(step.settle ?? 0.25)
    if let sf = step.seekFrom, let st = step.seekTo {
        let rate = step.fps ?? 30
        let total = Int(((st - sf) * rate).rounded())
        for f in 0..<total {
            evalJS("window.__quorumSeek(\(sf + Double(f) / rate));")
            snap(String(format: "%@/frame_%06d.png", outDir, frameIndex))
            frameIndex += 1
            if frameIndex % 300 == 0 { FileHandle.standardError.write("  frame \(frameIndex)\n".data(using: .utf8)!) }
        }
        continue
    }
    let count = step.frames ?? 1
    for f in 0..<count {
        if let from = step.scrollFrom, let to = step.scrollTo {
            let p = count > 1 ? Double(f) / Double(count - 1) : 1.0
            let e = p < 0.5 ? 4*p*p*p : 1 - pow(-2*p + 2, 3) / 2
            evalJS("window.scrollTo(0, \(from + (to - from) * e));")
        }
        snap(String(format: "%@/frame_%06d.png", outDir, frameIndex))
        frameIndex += 1
    }
    FileHandle.standardError.write("  step \(n+1)/\(steps.count) -> \(frameIndex) frames\n".data(using: .utf8)!)
}
print(frameIndex)
