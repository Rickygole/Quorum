import json
import os
import shutil
import sys
import wave

A = os.path.expanduser("~/quorum-submission/audio")
V2 = os.path.join(A, "v2")
FPS = 30

def clips(names, base):
    return [os.path.join(base, n) for n in names]

def lines(label, lead, gap):
    L = json.load(open(os.path.join(V2, "lines.json")))
    out = []
    t = lead
    for s in L[label]:
        out.append((os.path.join(V2, s["file"]), t))
        t += s["dur"] + gap
    return out

SEGMENTS = [
    {"name": "s1", "frames": "/tmp/seg_s1", "length": 16.0, "audio": [(os.path.join(A, "01_open.wav"), 1.0)]},
    {"name": "s2", "frames": "/tmp/seg_s2", "length": 25.0, "audio": [(os.path.join(A, "02_problem.wav"), 1.5)]},
    {"name": "s3", "frames": "/tmp/seg_s3", "length": 44.0, "audio": [(os.path.join(A, "03_hero.wav"), 1.5)]},
    {"name": "s4", "frames": "/tmp/seg_s4", "length": 30.0, "audio": [(os.path.join(A, "04_hard.wav"), 1.2)]},
    {"name": "s5", "frames": "/tmp/seg_s5", "length": 65.0, "audio": lines("arch", 1.0, 0.6)},
    {"name": "s6", "frames": "/tmp/seg_live", "length": 24.0, "audio": lines("live", 1.0, 0.6)},
    {"name": "s7", "frames": "/tmp/seg_s7", "length": 24.0, "audio": [(os.path.join(A, "06_arrives.wav"), 1.2)]},
    {"name": "s8", "frames": "/tmp/seg_s8", "length": 41.5, "audio": [(os.path.join(A, "07_eval.wav"), 0.6)]},
    {"name": "s9", "frames": "/tmp/seg_s9", "length": 20.0, "audio": [(os.path.join(A, "08_close.wav"), 1.5)]},
]

def build_frames(out_dir):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    idx = 0
    report = []
    for seg in SEGMENTS:
        src = sorted(f for f in os.listdir(seg["frames"]) if f.startswith("frame_") and f.endswith(".png"))
        want = int(round(seg["length"] * FPS))
        if not src:
            raise SystemExit(f"segment {seg['name']} has no frames")
        for i in range(want):
            f = src[min(i, len(src) - 1)]
            os.link(os.path.join(seg["frames"], f), os.path.join(out_dir, f"frame_{idx:06d}.png"))
            idx += 1
        report.append((seg["name"], len(src), want))
    return idx, report

def build_audio(out_path):
    with wave.open(SEGMENTS[0]["audio"][0][0], "rb") as w:
        params = w.getparams()
        rate = w.getframerate()
        width = w.getsampwidth()
    total = sum(int(round(s["length"] * rate)) for s in SEGMENTS)
    buf = bytearray(total * width)
    cursor = 0
    overruns = []
    for seg in SEGMENTS:
        seg_len = int(round(seg["length"] * rate))
        for path, start in seg["audio"]:
            with wave.open(path, "rb") as w:
                data = w.readframes(w.getnframes())
            off = cursor + int(round(start * rate))
            end = off + len(data) // width
            if end > cursor + seg_len:
                overruns.append((seg["name"], round((end - cursor - seg_len) / rate, 2)))
                data = data[: (cursor + seg_len - off) * width]
            buf[off * width: off * width + len(data)] = data
        cursor += seg_len
    with wave.open(out_path, "wb") as o:
        o.setparams(params)
        o.writeframes(bytes(buf))
    return total / rate, overruns

if __name__ == "__main__":
    frames_out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/final_frames"
    audio_out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/final_audio.wav"
    n, report = build_frames(frames_out)
    secs, overruns = build_audio(audio_out)
    for name, have, want in report:
        print(f"  {name}: captured {have} frames, used {want}{'  (held last frame)' if want > have else ''}")
    print(f"frames {n} = {n / FPS:.1f}s   audio {secs:.1f}s")
    print("audio overruns:", overruns or "none")
