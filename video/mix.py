import json
import os
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt, resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music

SR = 44100
ORDER = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9"]
LEAD = 0.35
GAP = 0.2
TAIL = {"s9": 3.2}
DEFAULT_TAIL = 0.6
MIN_LEN = {"s6": 16.0, "s5": 44.0, "s3": 30.0}
SECTIONS = {"s1": (0.55, 0.0), "s2": (0.8, 0.6), "s3": (0.85, 0.75), "s4": (0.8, 0.7), "s5": (0.9, 1.0),
            "s6": (0.9, 1.0), "s7": (0.8, 0.8), "s8": (0.7, 0.55), "s9": (1.0, 0.9)}

def read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, "<i4").astype(np.float64) / 2147483648.0
    else:
        x = (np.frombuffer(raw, "u1").astype(np.float64) - 128) / 128.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        from math import gcd
        g = gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g)
    return x

def trim_silence(x, thresh=0.004):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.02 * SR))
    b = min(len(x), idx[-1] + int(0.06 * SR))
    return x[a:b]

def voice_chain(x):
    x = sosfilt(butter(2, 90 / (SR / 2), "high", output="sos"), x)
    x = sosfilt(butter(4, 12500 / (SR / 2), "low", output="sos"), x)
    env = np.sqrt(np.convolve(x * x, np.ones(441) / 441, mode="same")) + 1e-9
    thresh = 0.08
    ratio = 3.0
    gain = np.where(env > thresh, (thresh + (env - thresh) / ratio) / env, 1.0)
    gain = np.convolve(gain, np.ones(220) / 220, mode="same")
    return x * gain

def write_wav(path, x):
    y = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())

def build(script_path, voice_dir, out_wav, out_json):
    script = json.load(open(script_path))
    timeline = []
    t = 0.0
    lines_all = []
    for seg in ORDER:
        start = t
        cursor = LEAD
        placed = []
        for i, _ in enumerate(script[seg]):
            clip = trim_silence(read_wav(os.path.join(voice_dir, f"{seg}_{i:02d}.wav")))
            clip = voice_chain(clip)
            placed.append((start + cursor, clip))
            cursor += len(clip) / SR + GAP
        cursor += TAIL.get(seg, DEFAULT_TAIL) - GAP
        length = max(cursor, MIN_LEN.get(seg, 0.0))
        timeline.append({"segment": seg, "start": round(start, 3), "length": round(length, 3),
                         "speech": round(cursor - LEAD - TAIL.get(seg, DEFAULT_TAIL) + GAP, 3)})
        lines_all.extend(placed)
        t += length
    total = t
    n = int(total * SR) + SR
    voice = np.zeros(n)
    for at, clip in lines_all:
        a = int(at * SR)
        voice[a:a + len(clip)] += clip
    rms = np.sqrt(np.mean(voice[np.abs(voice) > 0.01] ** 2))
    voice *= 0.2 / rms
    sections = [(s["start"], s["start"] + s["length"], *SECTIONS[s["segment"]]) for s in timeline]
    bed = music.render(total, sections)
    bed = np.concatenate([bed, np.zeros(n - len(bed))])
    bed *= 0.09 / (np.sqrt(np.mean(bed[bed != 0] ** 2)) + 1e-9)
    active = np.convolve((np.abs(voice) > 0.01).astype(float), np.ones(int(0.35 * SR)) / int(0.35 * SR), mode="same")
    duck = 1.0 - 0.55 * np.clip(active * 3, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    mix = voice + bed * duck
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / peak * 1.15) / np.tanh(1.15) * 0.93
    mix = mix[: int(total * SR)]
    write_wav(out_wav, mix)
    json.dump({"total": round(total, 3), "segments": timeline}, open(out_json, "w"), indent=1)
    return total, timeline

if __name__ == "__main__":
    total, tl = build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    for s in tl:
        print(f"  {s['segment']}: starts {s['start']:6.1f}s  length {s['length']:5.1f}s  speech {s['speech']:5.1f}s")
    print(f"TOTAL {total:.1f}s = {int(total // 60)}:{total % 60:04.1f}")
