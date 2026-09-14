import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100

def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)

def lowpass(x, hz, order=2):
    return sosfilt(butter(order, hz / (SR / 2), "low", output="sos"), x)

def envelope(n, attack, release):
    e = np.ones(n)
    a = min(n, int(attack * SR))
    r = min(n - a, int(release * SR))
    if a:
        e[:a] = np.linspace(0, 1, a) ** 2
    if r:
        e[n - r:] = np.linspace(1, 0, r) ** 2
    return e

def pad_chord(midis, seconds, rng):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        f = note(m)
        for det in (-0.07, 0.0, 0.07):
            ph = rng.uniform(0, 2 * np.pi)
            ff = f * (1 + det / 100 * 12)
            out += np.sin(2 * np.pi * ff * t + ph) * 0.5
            out += np.sin(2 * np.pi * ff * 2 * t + ph) * 0.12
    out *= envelope(n, 1.1, 1.4)
    return out / (len(midis) * 3)

def pluck(midi, seconds):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    f = note(midi)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t) + 0.12 * np.sin(2 * np.pi * f * 3 * t)
    return tone * np.exp(-t * 5.5) * envelope(n, 0.004, 0.05)

def bass(midi, seconds):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * note(midi) * t) * np.exp(-t * 1.6) * envelope(n, 0.01, 0.2)

PROGRESSION = [
    [50, 54, 57, 62],
    [45, 52, 57, 61],
    [47, 54, 59, 62],
    [43, 50, 55, 59],
]

def render(total_seconds, sections, bpm=96, seed=7):
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    n = int(total_seconds * SR) + SR
    pad = np.zeros(n)
    arp = np.zeros(n)
    low = np.zeros(n)
    t = 0.0
    i = 0
    while t < total_seconds + bar:
        chord = PROGRESSION[i % 4]
        s = int(t * SR)
        if s >= n:
            break
        seg = pad_chord(chord, bar * 1.25, rng)
        e = min(n, s + len(seg))
        pad[s:e] += seg[: e - s]
        b = bass(chord[0] - 12, bar)
        e = min(n, s + len(b))
        low[s:e] += b[: e - s]
        tones = [chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 12]
        for k in range(8):
            ps = int((t + k * beat / 2) * SR)
            p = pluck(tones[k % 4], beat * 1.2)
            e = min(n, ps + len(p))
            if ps < n:
                arp[ps:e] += p[: e - ps]
        t += bar
        i += 1
    pad = lowpass(pad, 2400)
    arp = lowpass(arp, 5200)
    low = lowpass(low, 180)
    tt = np.arange(n) / SR
    arp_gain = np.zeros(n)
    pad_gain = np.zeros(n)
    for start, end, pg, ag in sections:
        a, b = int(start * SR), int(end * SR)
        pad_gain[a:b] = pg
        arp_gain[a:b] = ag
    k = int(1.5 * SR)
    kernel = np.ones(k) / k
    pad_gain = np.convolve(pad_gain, kernel, mode="same")
    arp_gain = np.convolve(arp_gain, kernel, mode="same")
    mix = pad * pad_gain * 0.9 + arp * arp_gain * 0.22 + low * pad_gain * 0.35
    fade = np.ones(n)
    fi = int(2.0 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    end = int(total_seconds * SR)
    fo = int(3.0 * SR)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    mix *= fade
    return mix[: int(total_seconds * SR)]
