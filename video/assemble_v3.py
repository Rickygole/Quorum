import json
import os
import shutil
import sys

from PIL import Image

FPS = 30
BLEND = 5
SOURCES = {"s1": "/tmp/seg_s1", "s2": "/tmp/seg_s2", "s3": "/tmp/seg_s3", "s4": "/tmp/seg_s4",
           "s5": "/tmp/seg_s5", "s6": "/tmp/seg_live", "s7": "/tmp/seg_s7", "s8": "/tmp/seg_s8", "s9": "/tmp/seg_s9"}

def listing(d):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.startswith("frame_") and f.endswith(".png"))

def main(timing_path, out_dir):
    timing = json.load(open(timing_path))
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    plan = []
    for seg in timing["segments"]:
        src = listing(SOURCES[seg["segment"]])
        want = int(round(seg["length"] * FPS))
        frames = [src[min(len(src) - 1, int(i * len(src) / want))] for i in range(want)]
        plan.append((seg["segment"], frames, len(src)))
    idx = 0
    boundaries = []
    for k, (name, frames, have) in enumerate(plan):
        boundaries.append(idx)
        for f in frames:
            os.link(f, os.path.join(out_dir, f"frame_{idx:06d}.png"))
            idx += 1
        print(f"  {name}: {have} captured -> {len(frames)} frames ({have / max(1, len(frames)):.2f}x)")
    for b in boundaries[1:]:
        prev_last = Image.open(os.path.join(out_dir, f"frame_{b - 1:06d}.png")).convert("RGB")
        next_first = Image.open(os.path.join(out_dir, f"frame_{b:06d}.png")).convert("RGB")
        for j in range(BLEND):
            a = (j + 1) / (BLEND + 1) * 0.5
            p = os.path.join(out_dir, f"frame_{b - BLEND + j:06d}.png")
            base = Image.open(p).convert("RGB")
            os.remove(p)
            Image.blend(base, next_first, a).save(p, compress_level=1)
            q = os.path.join(out_dir, f"frame_{b + j:06d}.png")
            base2 = Image.open(q).convert("RGB")
            os.remove(q)
            Image.blend(prev_last, base2, 0.5 + (j + 1) / (BLEND + 1) * 0.5).save(q, compress_level=1)
    print(f"frames {idx} = {idx / FPS:.1f}s   timing total {timing['total']:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
