import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from mix import read_wav, write_wav, SR

MAX_PAUSE = 0.28

def tighten(x):
    frame = int(0.01 * SR)
    n = len(x) // frame
    energy = np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1))
    quiet = energy < 0.01
    keep = np.ones(n, bool)
    run = 0
    limit = int(MAX_PAUSE / 0.01)
    for i in range(n):
        run = run + 1 if quiet[i] else 0
        if run > limit:
            keep[i] = False
    pieces = [x[i * frame:(i + 1) * frame] for i in range(n) if keep[i]]
    return np.concatenate(pieces)

if __name__ == "__main__":
    y = tighten(read_wav(sys.argv[1]))
    write_wav(sys.argv[2], y)
    print(f"{sys.argv[2]}  {len(y) / SR:.2f}s")
