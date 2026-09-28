#!/usr/bin/env python3
"""Procedural sound effects for Brushfire, synthesised from scratch (sfxr-style, but in numpy).

Every sound is built from oscillators, filtered noise, envelopes and a little saturation, so the
whole soundset is reproducible and licence-free. Re-run after tweaking:

    python3 tools/sfx/generate_sfx.py            # writes game/audio/sfx/*.wav

Variants are written as name_1.wav, name_2.wav ...; the game picks one at random.
"""
import os
import wave

import numpy as np
from scipy import signal

SR = 32000
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "audio", "sfx")
rng = np.random.default_rng(1996)


# ----------------------------------------------------------------------------- building blocks

def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def brown(dur):
    w = rng.normal(0, 1, int(dur * SR))
    b = np.cumsum(w)
    b = signal.detrend(b)
    return b / (np.max(np.abs(b)) + 1e-9)


def env_exp(dur, decay, attack=0.001):
    t = t_axis(dur)
    e = np.exp(-t / max(decay, 1e-4))
    if attack > 0:
        e *= np.clip(t / attack, 0, 1)
    return e


def env_adsr(dur, a, d, s, r):
    n = int(dur * SR)
    t = t_axis(dur)
    e = np.zeros(n)
    for i, x in enumerate(t):
        if x < a:
            e[i] = x / a
        elif x < a + d:
            e[i] = 1 - (1 - s) * (x - a) / d
        elif x < dur - r:
            e[i] = s
        else:
            e[i] = s * max(0.0, (dur - x) / r)
    return e


def sweep_phase(f0, f1, dur, curve=1.0):
    t = t_axis(dur)
    k = (t / dur) ** curve
    f = f0 + (f1 - f0) * k
    return 2 * np.pi * np.cumsum(f) / SR


def sine_sweep(f0, f1, dur, curve=1.0):
    return np.sin(sweep_phase(f0, f1, dur, curve))


def saw_sweep(f0, f1, dur, curve=1.0):
    ph = sweep_phase(f0, f1, dur, curve) / (2 * np.pi)
    return 2 * (ph - np.floor(ph + 0.5))


def square_sweep(f0, f1, dur, curve=1.0, duty=0.5):
    ph = sweep_phase(f0, f1, dur, curve) / (2 * np.pi)
    return np.where((ph % 1.0) < duty, 1.0, -1.0)


def lp(x, cutoff, order=2):
    cutoff = min(cutoff, SR * 0.45)
    b, a = signal.butter(order, cutoff / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def hp(x, cutoff, order=2):
    b, a = signal.butter(order, cutoff / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    hi = min(hi, SR * 0.45)
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def sweep_lp(x, f0, f1, curve=1.0):
    """Time-varying one-pole low-pass (cheap filter sweep)."""
    n = len(x)
    k = (np.arange(n) / max(n - 1, 1)) ** curve
    fc = f0 + (f1 - f0) * k
    alpha = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def drive(x, amount):
    return np.tanh(x * amount) / np.tanh(amount)


def crush(x, bits=6, hold=2):
    q = 2 ** bits
    y = np.round(x * q) / q
    return np.repeat(y[::hold], hold)[:len(x)]


def pad(x, dur):
    n = int(dur * SR)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def at(x, delay, dur=None):
    """Delay a signal by `delay` seconds."""
    y = np.concatenate([np.zeros(int(delay * SR)), x])
    return pad(y, dur) if dur else y


def reverb(x, wet=0.25, room=0.5, tail=1.2):
    """Small Schroeder reverb: 4 combs + 2 allpasses."""
    x = np.concatenate([x, np.zeros(int(tail * SR))])
    combs = [0.0297, 0.0371, 0.0411, 0.0437]
    out = np.zeros_like(x)
    fb = 0.72 + 0.2 * room
    for d in combs:
        n = int(d * SR * (0.8 + room * 0.6))
        b = np.zeros(n + 1)
        b[n] = 1.0
        a = np.zeros(n + 1)
        a[0], a[n] = 1.0, -fb
        out += signal.lfilter(b, a, x)
    out /= len(combs)
    for d, g in ((0.005, 0.7), (0.0017, 0.7)):
        n = int(d * SR)
        b = np.zeros(n + 1)
        b[0], b[-1] = -g, 1
        a = np.zeros(n + 1)
        a[0], a[-1] = 1, -g
        out = signal.lfilter(b, a, out)
    out = lp(out, 5000)
    return x * (1 - wet) + out * wet


def metal_hit(freq, dur, decay, partials=(1.0, 2.76, 5.4, 8.93)):
    t = t_axis(dur)
    s = np.zeros_like(t)
    for i, p in enumerate(partials):
        s += np.sin(2 * np.pi * freq * p * t + rng.uniform(0, 6)) * np.exp(-t / (decay / (1 + i * 0.7))) / (1 + i)
    return s


def formant_voice(f0, f1, dur, formants=((700, 1.0), (1200, 0.6), (2600, 0.25)), breath=0.25):
    src = saw_sweep(f0, f1, dur, 0.7) + noise(dur) * breath
    out = np.zeros_like(src)
    for f, g in formants:
        out += bp(src, f * 0.85, f * 1.15) * g
    return out


def normalize(x, peak=0.89):
    x = x - np.mean(x)
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def fade(x, fin=0.002, fout=0.01):
    n = len(x)
    a, b = int(fin * SR), int(fout * SR)
    e = np.ones(n)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if b:
        e[-b:] = np.linspace(1, 0, b)
    return x * e


def save(name, x, peak=0.89, fin=0.001, fout=0.02):
    x = fade(normalize(x, peak), fin, fout)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name:26s} {len(x) / SR:5.2f}s")


def save_exact_loop(name, x, peak=0.8):
    """Loop whose length is already exact (e.g. whole bars of music): no crossfade, no fades."""
    x = normalize(x, peak)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name:26s} {len(x) / SR:5.2f}s (loop)")


def save_loop(name, x, peak=0.8, xfade=0.25):
    """Seamless loop: crossfade the tail into the head."""
    n = int(xfade * SR)
    head, body, tail = x[:n], x[n:-n], x[-n:]
    ramp = np.linspace(0, 1, n)
    joined = np.concatenate([body, tail * (1 - ramp) + head * ramp])
    joined = normalize(joined, peak)
    data = (np.clip(joined, -1, 1) * 32767).astype(np.int16)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name:26s} {len(joined) / SR:5.2f}s (loop)")


# ----------------------------------------------------------------------------- weapons

def gunshot(body_dur=0.35, low=70, bright=3500, crack=1.0, tail=0.6, dist=3.0):
    d = body_dur + tail
    click = pad(noise(0.004) * env_exp(0.004, 0.0015), d) * crack
    thump = pad(sine_sweep(low * 2.2, low, 0.25, 0.3) * env_exp(0.25, 0.06), d)
    body = pad(lp(noise(body_dur), bright) * env_exp(body_dur, body_dur * 0.25, 0.0005), d)
    grit = pad(bp(noise(body_dur), 1500, 6000) * env_exp(body_dur, 0.03), d) * 0.5
    room = pad(lp(noise(d), 900) * env_exp(d, tail * 0.3, 0.01), d) * 0.35
    s = click * 0.8 + thump * 1.0 + body * 0.9 + grit + room
    return drive(s, dist)


def shotgun_fire():
    return reverb(gunshot(0.4, 55, 3200, 1.0, 0.7, 3.5), wet=0.18, room=0.6, tail=0.6)


def shotgun_pump():
    d = 0.5
    back = mix(bp(noise(0.06), 1500, 7000) * env_exp(0.06, 0.015), metal_hit(1900, 0.1, 0.03) * 0.4)
    fwd = mix(bp(noise(0.05), 1200, 6000) * env_exp(0.05, 0.01), metal_hit(1300, 0.12, 0.04) * 0.5)
    slide = bp(noise(0.1), 3000, 9000) * env_adsr(0.1, 0.01, 0.05, 0.3, 0.04) * 0.25
    return mix(at(back, 0.0, d), at(slide, 0.03, d), at(fwd, 0.19, d))


def chaingun_fire():
    return reverb(gunshot(0.14, 90, 4800, 1.0, 0.25, 4.0), wet=0.12, room=0.4, tail=0.3)


def rocket_fire():
    d = 1.0
    thump = pad(sine_sweep(160, 45, 0.3, 0.5) * env_exp(0.3, 0.09), d)
    whoosh = noise(d) * env_adsr(d, 0.02, 0.2, 0.5, 0.6)
    whoosh = sweep_lp(whoosh, 5000, 600, 0.6)
    hiss = bp(noise(d), 2000, 8000) * env_exp(d, 0.15) * 0.4
    return drive(thump * 1.2 + whoosh * 0.8 + hiss, 2.0)


def rocket_fly():
    d = 2.0
    s = bp(noise(d), 300, 2500) * 0.7 + bp(noise(d), 4000, 9000) * 0.25
    s *= 1 + 0.15 * np.sin(2 * np.pi * 7 * t_axis(d))
    return s


def explosion():
    d = 2.2
    boom = pad(sine_sweep(90, 28, 1.0, 0.4) * env_exp(1.0, 0.35, 0.002), d)
    body = sweep_lp(noise(d), 6000, 120, 0.35) * env_exp(d, 0.55, 0.002)
    crackle = np.zeros(int(d * SR))
    for _ in range(90):
        pos = int(rng.exponential(0.25) * SR)
        if pos < len(crackle) - 400:
            crackle[pos:pos + 400] += bp(noise(400 / SR), 800, 5000) * env_exp(400 / SR, 0.003) * rng.uniform(0.2, 1)
    crackle *= env_exp(d, 0.5)
    s = drive(boom * 1.3 + body * 1.2 + crackle * 0.5, 2.5)
    return reverb(s, wet=0.3, room=0.8, tail=1.0)


def dry_fire():
    return metal_hit(2600, 0.08, 0.012) * 0.6 + bp(noise(0.08), 2000, 8000) * env_exp(0.08, 0.006)


def weapon_switch():
    d = 0.35
    a = metal_hit(900, 0.2, 0.05) * 0.6 + bp(noise(0.2), 1000, 5000) * env_exp(0.2, 0.01)
    b = metal_hit(1400, 0.15, 0.03) * 0.5 + bp(noise(0.15), 2000, 7000) * env_exp(0.15, 0.008)
    return mix(at(a, 0, d), at(b, 0.12, d))


def chaingun_windup():
    d = 0.45
    s = saw_sweep(60, 240, d, 0.6) * 0.4 + sine_sweep(120, 480, d, 0.6) * 0.3
    s = lp(s, 2500) * env_adsr(d, 0.05, 0.1, 0.8, 0.1)
    return s + bp(noise(d), 3000, 6000) * 0.05


def hit_marker():
    return sine_sweep(2400, 2200, 0.05) * env_exp(0.05, 0.012) + metal_hit(3200, 0.05, 0.01) * 0.3


def kill_marker():
    return mix(sine_sweep(900, 1100, 0.12) * env_exp(0.12, 0.05), at(sine_sweep(1350, 1500, 0.12) * env_exp(0.12, 0.05), 0.06))


# ----------------------------------------------------------------------------- player

def footstep():
    d = 0.18
    thud = sine_sweep(120, 60, 0.08) * env_exp(0.08, 0.02)
    scuff = lp(noise(d), 1800) * env_exp(d, 0.025, 0.002)
    grit = bp(noise(d), 2500, 7000) * env_exp(d, 0.012) * rng.uniform(0.2, 0.5)
    return mix(pad(thud, d) * 0.8, scuff * 0.9, grit)


def player_jump():
    d = 0.18
    cloth = bp(noise(d), 800, 3500) * env_adsr(d, 0.02, 0.05, 0.3, 0.08)
    breath = formant_voice(180, 150, d, ((500, 0.8), (1500, 0.3)), breath=1.2) * env_adsr(d, 0.02, 0.06, 0.2, 0.08)
    return cloth * 0.6 + breath * 0.25


def player_land():
    d = 0.35
    thud = sine_sweep(110, 45, 0.2, 0.5) * env_exp(0.2, 0.05)
    body = lp(noise(d), 900) * env_exp(d, 0.05, 0.001)
    grit = bp(noise(d), 2000, 6000) * env_exp(d, 0.02) * 0.4
    return drive(mix(pad(thud, d) * 1.2, body, grit), 1.5)


def player_hurt(pitch):
    d = 0.32
    v = formant_voice(pitch * 1.25, pitch * 0.85, d, ((650, 1.0), (1100, 0.7), (2500, 0.2)), breath=0.4)
    return drive(v * env_adsr(d, 0.01, 0.08, 0.6, 0.15), 2.0)


def player_death():
    d = 1.3
    v = formant_voice(170, 70, d, ((600, 1.0), (1000, 0.6), (2400, 0.2)), breath=0.5)
    v *= env_adsr(d, 0.02, 0.2, 0.7, 0.7)
    thud = at(sine_sweep(100, 40, 0.3, 0.5) * env_exp(0.3, 0.08) + lp(noise(0.3), 700) * env_exp(0.3, 0.05), 0.9, d)
    return reverb(drive(v, 1.8) + thud, wet=0.2, room=0.5, tail=0.6)


# ----------------------------------------------------------------------------- pickups & ui

def chime(freqs, step, d, decay=0.25, shape="sine"):
    out = np.zeros(int(d * SR))
    for i, f in enumerate(freqs):
        t = t_axis(d - i * step)
        if shape == "bell":
            tone = np.sin(2 * np.pi * f * t + 1.5 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.2))
        else:
            tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
        out += at(tone * np.exp(-t / decay) * np.clip(t / 0.004, 0, 1), i * step, d)
    return out


def pickup_health():
    return reverb(chime([523.25, 659.25, 783.99, 1046.5], 0.055, 0.7), wet=0.2, tail=0.4)


def pickup_armor():
    s = chime([392.0, 587.33, 783.99], 0.07, 0.8, 0.35, "bell")
    shimmer = bp(noise(0.8), 5000, 9000) * env_adsr(0.8, 0.05, 0.2, 0.2, 0.4) * 0.15
    return reverb(s + shimmer, wet=0.25, tail=0.5)


def pickup_ammo():
    d = 0.4
    clack = metal_hit(700, 0.2, 0.05) * 0.5 + bp(noise(0.2), 1500, 6000) * env_exp(0.2, 0.01)
    clack2 = metal_hit(1100, 0.2, 0.04) * 0.4 + bp(noise(0.2), 2000, 7000) * env_exp(0.2, 0.008)
    return mix(at(clack, 0, d), at(clack2, 0.09, d), at(chime([880], 0, 0.25, 0.08) * 0.3, 0.1, d))


def pickup_weapon():
    d = 1.0
    chord = sum(saw_sweep(f, f, d) for f in (110, 164.8, 220)) / 3
    chord = lp(chord, 1800) * env_adsr(d, 0.01, 0.2, 0.4, 0.5)
    return reverb(drive(chord, 2.0) * 0.7 + chime([659.25, 987.77], 0.08, d, 0.3) * 0.5 + pad(weapon_switch(), d) * 0.6,
                  wet=0.2, tail=0.5)


def ui_click():
    return sine_sweep(1800, 1200, 0.04) * env_exp(0.04, 0.01) + bp(noise(0.04), 3000, 8000) * env_exp(0.04, 0.003) * 0.3


def ui_hover():
    return sine_sweep(900, 1000, 0.05) * env_exp(0.05, 0.015) * 0.5


def level_complete():
    d = 2.2
    notes = [261.63, 311.13, 392.0, 523.25, 466.16, 523.25, 622.25, 783.99]
    steps = [0, 0.14, 0.28, 0.42, 0.7, 0.84, 0.98, 1.12]
    out = np.zeros(int(d * SR))
    for f, s in zip(notes, steps):
        nd = d - s
        tone = saw_sweep(f, f, nd) * 0.5 + square_sweep(f * 0.5, f * 0.5, nd) * 0.3
        tone = lp(tone, 2400) * env_adsr(nd, 0.01, 0.1, 0.5, min(0.8, nd * 0.5)) * np.exp(-t_axis(nd) / 0.6)
        out += at(tone, s, d)
    return reverb(out, wet=0.3, room=0.7, tail=0.8)


def secret_found():
    return reverb(chime([587.33, 739.99, 880.0, 1174.66, 1479.98], 0.07, 1.0, 0.4, "bell"), wet=0.3, tail=0.6)


def jump_pad():
    d = 0.6
    s = sine_sweep(120, 700, d, 0.4) * env_adsr(d, 0.005, 0.1, 0.5, 0.3)
    w = sweep_lp(noise(d), 800, 5000, 0.5) * env_adsr(d, 0.02, 0.2, 0.4, 0.3) * 0.5
    return drive(s + w, 1.5)


# ----------------------------------------------------------------------------- enemies

def robot_chirp(f0, f1, d, mod=35):
    t = t_axis(d)
    car = sweep_phase(f0, f1, d, 0.8)
    s = np.sin(car + 2.5 * np.sin(2 * np.pi * mod * t))
    s *= env_adsr(d, 0.01, 0.05, 0.8, d * 0.3)
    return crush(s, 5, 3)


def enemy_alert(i):
    d = 0.55
    a = robot_chirp([600, 900, 400][i], [1400, 500, 1200][i], 0.2, [30, 55, 22][i])
    b = robot_chirp([1200, 700, 1000][i], [700, 1300, 500][i], 0.25, [45, 25, 60][i])
    return reverb(mix(at(a, 0, d), at(b, 0.2, d)), wet=0.2, tail=0.4)


def enemy_fire():
    d = 0.35
    zap = square_sweep(1900, 220, 0.16, 0.5, 0.35) * env_exp(0.16, 0.06)
    zap = lp(zap, 5000)
    body = gunshot(0.1, 110, 3000, 0.6, 0.15, 2.5)
    return reverb(mix(pad(zap, d) * 0.6, pad(body, d) * 0.7), wet=0.15, tail=0.3)


def plasma_fire():
    d = 0.45
    t = t_axis(d)
    s = np.sin(sweep_phase(700, 180, d, 0.5) + 3 * np.sin(2 * np.pi * 60 * t)) * env_exp(d, 0.12, 0.003)
    bub = bp(noise(d), 300, 1200) * env_exp(d, 0.08) * 0.4
    return reverb(s + bub, wet=0.2, tail=0.3)


def plasma_impact():
    d = 0.5
    sizzle = bp(noise(d), 1500, 9000) * env_exp(d, 0.12, 0.001)
    pop = sine_sweep(400, 90, 0.15) * env_exp(0.15, 0.04)
    return mix(sizzle * 0.7, pad(pop, d))


def enemy_hurt(i):
    d = 0.3
    clank = metal_hit([420, 510, 380][i], d, 0.08)
    glitch = crush(square_sweep([800, 1100, 650][i], [300, 600, 900][i], d, 1.0, 0.3), 3, 8) * env_exp(d, 0.05) * 0.4
    return mix(clank, glitch)


def enemy_death(i):
    d = 1.4
    zap = crush(saw_sweep([900, 700][i], 60, 0.7, 0.5), 4, 4) * env_exp(0.7, 0.25)
    crackle = bp(noise(d), 2000, 8000) * np.clip(rng.normal(0, 1, int(d * SR)), -3, 3) * env_exp(d, 0.3) * 0.3
    boom = pad(explosion()[: int(d * SR)], d) * 0.6
    return mix(pad(zap, d) * 0.7, crackle, boom)


def brute_roar():
    d = 1.2
    v = formant_voice(75, 55, d, ((350, 1.0), (800, 0.8), (1900, 0.3)), breath=0.7)
    v = drive(v * env_adsr(d, 0.08, 0.2, 0.8, 0.4), 3.0)
    growl = v * (1 + 0.4 * np.sin(2 * np.pi * 23 * t_axis(d)))
    return reverb(growl, wet=0.25, room=0.7, tail=0.6)


def brute_attack():
    d = 0.5
    swoosh = sweep_lp(noise(d), 400, 3500, 0.5) * env_adsr(d, 0.1, 0.1, 0.3, 0.2)
    hit = at(drive(sine_sweep(140, 50, 0.25) * env_exp(0.25, 0.06) + lp(noise(0.25), 1200) * env_exp(0.25, 0.03), 2.0), 0.22, d)
    return mix(swoosh * 0.6, hit)


def brute_step():
    d = 0.4
    thud = sine_sweep(80, 35, 0.3, 0.5) * env_exp(0.3, 0.09)
    clank = metal_hit(260, d, 0.06) * 0.25
    return mix(pad(drive(thud, 2), d), clank, lp(noise(d), 500) * env_exp(d, 0.04) * 0.6)


def drone_hum():
    d = 3.0
    t = t_axis(d)
    # frequencies chosen to complete whole cycles in 3 s so the loop is seamless
    s = saw_sweep(88, 88, d) * 0.5 + saw_sweep(88.333, 88.333, d) * 0.5 + np.sin(2 * np.pi * 176 * t) * 0.4
    s = lp(s, 700)
    s *= 1 + 0.25 * np.sin(2 * np.pi * 4 * t)
    return s + bp(noise(d), 2000, 5000) * 0.03


def impact(i):
    d = 0.35
    snap = bp(noise(0.03), 1500, 9000) * env_exp(0.03, 0.004)
    chunk = lp(noise(0.12), 2500) * env_exp(0.12, 0.02) * 0.6
    out = mix(pad(snap, d), pad(chunk, d))
    if i in (1, 3):  # ricochet whine
        f0 = rng.uniform(2800, 4200)
        ric = sine_sweep(f0, f0 * 0.55, 0.3, 0.7) * env_adsr(0.3, 0.005, 0.05, 0.4, 0.2) * 0.35
        out = mix(out, at(ric, 0.01, d))
    return out


def impact_metal(i):
    d = 0.4
    return mix(metal_hit([780, 1020, 640][i], d, 0.06) * 0.7, pad(bp(noise(0.03), 2000, 9000) * env_exp(0.03, 0.004), d))


def door_open():
    d = 1.2
    hiss = bp(noise(d), 2500, 9000) * env_adsr(d, 0.02, 0.2, 0.3, 0.6) * 0.5
    motor = lp(saw_sweep(55, 70, d), 400) * env_adsr(d, 0.1, 0.2, 0.7, 0.3) * 0.6
    clunk = at(metal_hit(180, 0.4, 0.08) + lp(noise(0.4), 600) * env_exp(0.4, 0.03), 0.95, d)
    return reverb(mix(hiss, motor, clunk * 0.8), wet=0.2, tail=0.4)


def door_close():
    d = 1.1
    motor = lp(saw_sweep(70, 50, d), 400) * env_adsr(d, 0.05, 0.2, 0.7, 0.2) * 0.6
    slam = at(drive(sine_sweep(120, 45, 0.3) * env_exp(0.3, 0.08) + lp(noise(0.3), 900) * env_exp(0.3, 0.04), 2.0)
              + metal_hit(220, 0.3, 0.1) * 0.4, 0.8, d)
    return reverb(mix(motor, slam), wet=0.25, tail=0.5)


def lava_burn():
    d = 0.4
    return bp(noise(d), 1000, 7000) * env_exp(d, 0.1) + sine_sweep(300, 120, d) * env_exp(d, 0.08) * 0.3


# ----------------------------------------------------------------------------- water (Undercity)
# openspec/changes/water-and-swimming, design sections 2, 3a and 6.

def bubbles(d, count, f_lo, f_hi):
    """Bubble plinks: short upward sine chirps scattered over d seconds."""
    out = np.zeros(int(d * SR))
    for _ in range(count):
        t0 = rng.uniform(0, d * 0.75)
        f = rng.uniform(f_lo, f_hi)
        bd = rng.uniform(0.02, 0.06)
        b = sine_sweep(f, f * 1.7, bd, 0.5) * env_exp(bd, bd * 0.4, 0.002) * rng.uniform(0.2, 0.6)
        out += at(b, t0, d)
    return out


def water_splash(i):
    """Falling into water: a slap, a spray and bubbles, bigger for later variants."""
    d = 0.9 + 0.1 * i
    slap = sine_sweep(120, 45, 0.22) * env_exp(0.22, 0.05) * 0.8
    body = lp(noise(d), 2200 + 300 * i) * env_exp(d, 0.16 + 0.03 * i, 0.004)
    spray = bp(noise(d), 2500, 9000) * env_exp(d, 0.08, 0.002) * 0.45
    return mix(pad(slap, d), body, spray, bubbles(d, 14 + 5 * i, 350, 1300) * 0.7)


def swim_stroke(i):
    """One arm stroke: water pushed and dripping."""
    d = 0.5
    swish = sweep_lp(noise(d), 450 + 60 * i, 2000, 0.7) * env_adsr(d, 0.12, 0.12, 0.3, 0.2)
    return mix(swish * 0.8, bubbles(d, 5, 700, 1800) * 0.35)


def swim_stroke_tired(i):
    """A slower stroke with a heavy breath: stamina is low."""
    d = 0.7
    breath = formant_voice(150, 118, 0.55, ((450, 0.9), (1300, 0.3)), breath=1.6) * env_adsr(0.55, 0.08, 0.15, 0.5, 0.25)
    return mix(pad(swim_stroke(i), d) * 0.7, at(breath * 0.5, 0.12, d))


def breath_gasp():
    """Surfacing short of air."""
    d = 0.7
    inhale = formant_voice(210, 260, d, ((700, 1.0), (1600, 0.4), (2800, 0.15)), breath=2.0)
    return drive(inhale * env_adsr(d, 0.03, 0.1, 0.6, 0.3), 1.5) * 0.7


# ----------------------------------------------------------------------------- ambience / music

def ambience_industrial():
    d = 24.0
    t = t_axis(d)
    rumble = lp(brown(d), 160) * 0.9
    hum = (np.sin(2 * np.pi * 50 * t) * 0.25 + np.sin(2 * np.pi * 100 * t) * 0.12 + np.sin(2 * np.pi * 150 * t) * 0.05)
    hum *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.083 * t)
    air = bp(noise(d), 300, 1400) * 0.08 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t))
    clanks = np.zeros(len(t))
    for s in (2.5, 7.1, 11.8, 15.2, 19.9):
        c = metal_hit(rng.uniform(90, 220), 1.5, 0.4) * 0.35
        c = lp(c, 1200)
        i = int(s * SR)
        clanks[i:i + len(c)] += c[: len(clanks) - i]
    clanks = reverb(clanks, wet=0.6, room=0.9, tail=0.0)[: len(t)]
    return rumble + hum + air + clanks


def music_loop():
    """A short, moody industrial groove (A minor, 104 BPM, 8 bars)."""
    bpm = 104
    beat = 60 / bpm
    bars = 8
    d = bars * 4 * beat
    n = int(d * SR)
    out = np.zeros(n)

    def place(x, time, gain=1.0):
        i = int(time * SR)
        if i >= n:
            return
        seg = x[: n - i]
        out[i:i + len(seg)] += seg * gain

    kick = drive(sine_sweep(150, 42, 0.35, 0.3) * env_exp(0.35, 0.11), 2.0)
    snare = mix(bp(noise(0.25), 900, 7000) * env_exp(0.25, 0.06), sine_sweep(220, 180, 0.12) * env_exp(0.12, 0.04) * 0.5)
    hat = hp(noise(0.05), 7000) * env_exp(0.05, 0.012)
    for bar in range(bars):
        base = bar * 4 * beat
        for k in (0, 1.5, 2.0, 3.5 if bar % 2 else 2.75):
            place(kick, base + k * beat, 0.9)
        for s in (1, 3):
            place(snare, base + s * beat, 0.45)
        for h in range(8):
            place(hat, base + h * beat / 2, 0.12 if h % 2 else 0.2)
    roots = [55.0, 55.0, 43.65, 49.0]  # A, A, F, G
    for bar in range(bars):
        root = roots[bar % 4]
        for step in range(8):
            f = root * (2 if step in (3, 6) else 1)
            nd = beat / 2 * 0.9
            note = lp(saw_sweep(f, f, nd) + square_sweep(f * 0.5, f * 0.5, nd) * 0.5, 600) * env_adsr(nd, 0.005, 0.05, 0.7, 0.05)
            place(note, bar * 4 * beat + step * beat / 2, 0.35)
    pad_notes = [(220.0, 261.63, 329.63), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]
    for bar in range(bars):
        nd = 4 * beat
        chord = sum(saw_sweep(f, f, nd) + saw_sweep(f * 1.004, f * 1.004, nd) for f in pad_notes[bar % 4])
        chord = lp(chord, 1400) * env_adsr(nd, 0.4, 0.5, 0.6, 0.6)
        place(chord, bar * 4 * beat, 0.05)
    wet = reverb(out, wet=0.15, room=0.6, tail=1.0)
    looped = wet[:n].copy()
    looped[: len(wet) - n] += wet[n:]  # wrap the reverb tail to the start so the loop is seamless
    return looped


# ----------------------------------------------------------------------------- hub combat
# (openspec/changes/archive/2026-09-28-hub-combat, design section 8)

def kestrel_fire():
    """The Kestrel 10mm: a pistol's short, bright crack with a hard slap and a small room tail."""
    return reverb(gunshot(0.16, 110, 5200, 1.2, 0.3, 3.2), wet=0.14, room=0.45, tail=0.4)


def mersec_pistol_fire():
    """MerSec's service pistol: the same class of round, a touch duller, so the runner can tell
    whose shot it was."""
    return reverb(gunshot(0.18, 95, 4200, 1.0, 0.35, 3.0), wet=0.16, room=0.5, tail=0.45)


def kestrel_reload():
    """Magazine out, a new one seated with a slap, the slide let go: three metal clicks over 1.2 s."""
    d = 1.3
    out_ = mix(metal_hit(1700, 0.1, 0.025) * 0.5, bp(noise(0.05), 1500, 6000) * env_exp(0.05, 0.012))
    seat = mix(metal_hit(1100, 0.14, 0.035) * 0.7, bp(noise(0.06), 800, 5000) * env_exp(0.06, 0.01) * 1.2)
    slide = mix(bp(noise(0.08), 2500, 9000) * env_adsr(0.08, 0.005, 0.03, 0.3, 0.03) * 0.4,
                metal_hit(2100, 0.12, 0.03) * 0.6)
    return mix(at(out_, 0.05, d), at(seat, 0.6, d), at(slide, 1.05, d))


def baton_swing():
    """A baton cutting the air: a quick band-passed whoosh that rises and falls."""
    d = 0.35
    whoosh = sweep_lp(noise(d), 400, 2600, 0.6) * env_adsr(d, 0.08, 0.12, 0.3, 0.12)
    return hp(whoosh, 150) * 0.8


def main():
    save("shotgun_fire", shotgun_fire())
    save("shotgun_pump", shotgun_pump())
    for i in range(1, 4):
        save(f"chaingun_fire_{i}", chaingun_fire())
    save("chaingun_windup", chaingun_windup())
    save("rocket_fire", rocket_fire())
    save_loop("rocket_fly", rocket_fly())
    for i in range(1, 4):
        save(f"explosion_{i}", explosion())
    save("dry_fire", dry_fire())
    save("weapon_switch", weapon_switch())
    save("hit_marker", hit_marker())
    save("kill_marker", kill_marker())
    for i in range(1, 7):
        save(f"footstep_{i}", footstep(), peak=0.7)
    save("player_jump", player_jump())
    save("player_land", player_land())
    for i, p in enumerate((150, 125, 170), 1):
        save(f"player_hurt_{i}", player_hurt(p))
    save("player_death", player_death())
    save("pickup_health", pickup_health())
    save("pickup_armor", pickup_armor())
    save("pickup_ammo", pickup_ammo())
    save("pickup_weapon", pickup_weapon())
    save("ui_click", ui_click())
    save("ui_hover", ui_hover(), peak=0.5)
    save("level_complete", level_complete())
    save("secret_found", secret_found())
    save("jump_pad", jump_pad())
    for i in range(3):
        save(f"enemy_alert_{i + 1}", enemy_alert(i))
        save(f"enemy_hurt_{i + 1}", enemy_hurt(i))
    save("enemy_fire", enemy_fire())
    save("plasma_fire", plasma_fire())
    save("plasma_impact", plasma_impact())
    for i in range(2):
        save(f"enemy_death_{i + 1}", enemy_death(i))
    save("brute_roar", brute_roar())
    save("brute_attack", brute_attack())
    save("brute_step", brute_step(), peak=0.75)
    save_loop("drone_hum", drone_hum(), xfade=0.2)
    for i in range(4):
        save(f"impact_{i + 1}", impact(i))
    for i in range(3):
        save(f"impact_metal_{i + 1}", impact_metal(i))
    save("door_open", door_open())
    save("door_close", door_close())
    save("lava_burn", lava_burn())
    save_loop("ambience_industrial", ambience_industrial(), peak=0.6, xfade=1.5)
    save_exact_loop("music_loop", music_loop(), peak=0.7)
    # water, last so the seeded sounds above stay as they were
    for i in range(3):
        save(f"water_splash_{i + 1}", water_splash(i))
        save(f"swim_stroke_{i + 1}", swim_stroke(i), peak=0.6)
    for i in range(2):
        save(f"swim_stroke_tired_{i + 1}", swim_stroke_tired(i), peak=0.65)
    save("breath_gasp", breath_gasp(), peak=0.7)
    # hub combat, after water for the same reason
    save("kestrel_fire", kestrel_fire())
    save("mersec_pistol_fire", mersec_pistol_fire())
    save("kestrel_reload", kestrel_reload(), peak=0.7)
    save("baton_swing", baton_swing(), peak=0.6)


if __name__ == "__main__":
    main()
