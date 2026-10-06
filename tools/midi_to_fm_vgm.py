#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import struct
import sys


FNUM = (644, 681, 722, 765, 810, 858, 910, 964, 1021, 1081, 1145, 1213)
YM_CH_CODE = (0, 1, 2, 4, 5, 6)


PATCHES = (
    {
        "name": "lead",
        "mul": (0x71, 0x31, 0x21, 0x11),
        "tl":  (0x23, 0x2A, 0x25, 0x00),
        "ar":  (0x5F, 0x5F, 0x5F, 0x5F),
        "d1r": (0x12, 0x10, 0x14, 0x08),
        "d2r": (0x05, 0x05, 0x05, 0x04),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x32,
        "pan": 0xC0,
    },
    {
        "name": "bass",
        "mul": (0x01, 0x01, 0x02, 0x01),
        "tl":  (0x19, 0x24, 0x1A, 0x00),
        "ar":  (0x5F, 0x5F, 0x5F, 0x5F),
        "d1r": (0x10, 0x0C, 0x0B, 0x08),
        "d2r": (0x05, 0x04, 0x04, 0x03),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x31,
        "pan": 0xC0,
    },
    {
        "name": "metal",
        "mul": (0x32, 0x72, 0x34, 0x12),
        "tl":  (0x20, 0x22, 0x1D, 0x00),
        "ar":  (0x5F, 0x5F, 0x5F, 0x5F),
        "d1r": (0x17, 0x15, 0x18, 0x10),
        "d2r": (0x08, 0x08, 0x08, 0x06),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x35,
        "pan": 0xC0,
    },
    {
        "name": "bright",
        "mul": (0x41, 0x51, 0x21, 0x11),
        "tl":  (0x28, 0x25, 0x20, 0x00),
        "ar":  (0x5F, 0x5F, 0x5F, 0x5F),
        "d1r": (0x1C, 0x18, 0x18, 0x0E),
        "d2r": (0x09, 0x08, 0x08, 0x05),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x36,
        "pan": 0xC0,
    },
    {
        "name": "pad",
        "mul": (0x31, 0x21, 0x11, 0x11),
        "tl":  (0x2F, 0x30, 0x28, 0x05),
        "ar":  (0x4F, 0x4F, 0x4F, 0x4F),
        "d1r": (0x08, 0x08, 0x08, 0x06),
        "d2r": (0x03, 0x03, 0x03, 0x02),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x34,
        "pan": 0xC0,
    },
    {
        "name": "octave",
        "mul": (0x01, 0x12, 0x01, 0x21),
        "tl":  (0x24, 0x27, 0x1E, 0x00),
        "ar":  (0x5F, 0x5F, 0x5F, 0x5F),
        "d1r": (0x13, 0x12, 0x10, 0x08),
        "d2r": (0x06, 0x06, 0x05, 0x04),
        "rr":  (0x2F, 0x2F, 0x2F, 0x2F),
        "alg": 0x37,
        "pan": 0xC0,
    },
)


def read_vlq(data, pos):
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            return value, pos


def parse_track(data):
    pos = 0
    tick = 0
    running = None
    events = []
    while pos < len(data):
        delta, pos = read_vlq(data, pos)
        tick += delta
        status = data[pos]
        if status & 0x80:
            pos += 1
            if status < 0xF0:
                running = status
        elif running is not None:
            status = running
        else:
            raise ValueError("running status without previous status")

        if status == 0xFF:
            meta = data[pos]
            pos += 1
            size, pos = read_vlq(data, pos)
            payload = data[pos:pos + size]
            pos += size
            if meta == 0x2F:
                break
            if meta == 0x51 and size == 3:
                tempo = (payload[0] << 16) | (payload[1] << 8) | payload[2]
                events.append((tick, "tempo", tempo))
            continue

        if status in (0xF0, 0xF7):
            size, pos = read_vlq(data, pos)
            pos += size
            continue

        kind = status & 0xF0
        channel = status & 0x0F
        if kind in (0xC0, 0xD0):
            pos += 1
            continue

        a = data[pos]
        b = data[pos + 1]
        pos += 2
        if kind == 0x90 and b:
            events.append((tick, "on", channel, a, b))
        elif kind == 0x80 or kind == 0x90:
            events.append((tick, "off", channel, a))
    return events


def parse_midi(path):
    data = open(path, "rb").read()
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, tracks, division = struct.unpack(">HHH", data[8:14])
    if fmt == 2:
        raise ValueError("MIDI format 2 is not supported")
    if division & 0x8000:
        raise ValueError("SMPTE time division is not supported")
    pos = 8 + header_len
    events = []
    for track in range(tracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError("missing MTrk chunk")
        size = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        pos += 8
        for ev in parse_track(data[pos:pos + size]):
            events.append((ev[0], track) + ev[1:])
        pos += size
    return division, events


def seconds_by_tick(events, ppq):
    tempos = sorted((tick, value) for tick, _track, kind, value, *rest in events
                    if kind == "tempo")
    if not tempos or tempos[0][0] != 0:
        tempos.insert(0, (0, 500000))
    segments = []
    last_tick = tempos[0][0]
    last_sec = 0.0
    last_tempo = tempos[0][1]
    segments.append((last_tick, last_sec, last_tempo))
    for tick, tempo in tempos[1:]:
        last_sec += (tick - last_tick) * last_tempo / (ppq * 1000000.0)
        last_tick = tick
        last_tempo = tempo
        segments.append((last_tick, last_sec, last_tempo))

    def convert(tick):
        seg = segments[0]
        for candidate in segments:
            if candidate[0] > tick:
                break
            seg = candidate
        base_tick, base_sec, tempo = seg
        return base_sec + (tick - base_tick) * tempo / (ppq * 1000000.0)

    return convert


def ym_write(port, reg, value):
    return bytes((0x52 if port == 0 else 0x53, reg & 0xFF, value & 0xFF))


def psg_write(value):
    return bytes((0x50, value & 0xFF))


def psg_volume(channel, volume):
    return psg_write(0x90 | (channel << 5) | (volume & 0x0F))


def psg_tone(channel, period):
    return psg_write(0x80 | (channel << 5) | (period & 0x0F)) + \
        psg_write((period >> 4) & 0x3F)


def psg_noise(control):
    return psg_write(0xE0 | (control & 0x07))


def ch_port_index(ch):
    return (0, ch) if ch < 3 else (1, ch - 3)


def ym_ch_write(ch, reg, value):
    port, idx = ch_port_index(ch)
    return ym_write(port, reg + idx, value)


def key_off(ch):
    return ym_write(0, 0x28, YM_CH_CODE[ch])


def key_on(ch):
    return ym_write(0, 0x28, 0xF0 | YM_CH_CODE[ch])


def note_freq(note):
    octave = max(0, min(7, note // 12 - 1))
    return FNUM[note % 12], octave


def set_note(ch, note):
    fnum, block = note_freq(note)
    return ym_ch_write(ch, 0xA4, (block << 3) | ((fnum >> 8) & 0x07)) + \
        ym_ch_write(ch, 0xA0, fnum & 0xFF)


def set_patch(ch, patch):
    out = bytearray()
    op_offsets = (0, 4, 8, 12)
    for i, op in enumerate(op_offsets):
        out += ym_ch_write(ch, 0x30 + op, patch["mul"][i])
        out += ym_ch_write(ch, 0x40 + op, patch["tl"][i])
        out += ym_ch_write(ch, 0x50 + op, patch["ar"][i])
        out += ym_ch_write(ch, 0x60 + op, patch["d1r"][i])
        out += ym_ch_write(ch, 0x70 + op, patch["d2r"][i])
        out += ym_ch_write(ch, 0x80 + op, patch["rr"][i])
        out += ym_ch_write(ch, 0x90 + op, 0x00)
    out += ym_ch_write(ch, 0xB0, patch["alg"])
    out += ym_ch_write(ch, 0xB4, patch["pan"])
    return bytes(out)


def build_init():
    out = bytearray()
    out += ym_write(0, 0x22, 0x00)
    out += ym_write(0, 0x27, 0x00)
    out += ym_write(0, 0x2B, 0x00)
    for ch in range(6):
        out += key_off(ch)
        out += set_patch(ch, PATCHES[ch])
    for ch in range(4):
        out += psg_volume(ch, 15)
    return bytes(out)


def choose_voice(voices):
    for i, voice in enumerate(voices):
        if voice is None:
            return i
    return min(range(len(voices)), key=lambda i: voices[i]["order"])


def drum_hit(note):
    if note in (35, 36):
        return psg_noise(0x04) + psg_volume(3, 2), 4
    if note in (38, 40):
        return psg_noise(0x07) + psg_volume(3, 3), 5
    if note in (42, 44, 46):
        return psg_noise(0x06) + psg_volume(3, 5), 2
    if note in (49, 51, 52, 55, 57, 59):
        return psg_noise(0x05) + psg_volume(3, 4), 6
    if note in (45, 47, 48, 50):
        return psg_tone(2, 0x40) + psg_volume(2, 5), 5
    return psg_noise(0x06) + psg_volume(3, 5), 3


def build_vgm(in_mid):
    ppq, events = parse_midi(in_mid)
    to_sec = seconds_by_tick(events, ppq)
    musical = []
    seq = 0
    for ev in events:
        tick, track, kind, *rest = ev
        if kind in ("on", "off"):
            frame = int(round(to_sec(tick) * 60.0))
            musical.append((frame, seq, track, kind, rest))
            seq += 1
    musical.sort()

    init = build_init()
    data = bytearray(init)
    loop_data_offset = len(data)
    voices = [None] * 6
    active = {}
    psg_mute = {}
    pos = 0
    frame = 0
    last_frame = max((e[0] for e in musical), default=0) + 60
    while frame <= last_frame:
        for ch, end_frame in list(psg_mute.items()):
            if end_frame <= frame:
                data += psg_volume(ch, 15)
                del psg_mute[ch]

        while pos < len(musical) and musical[pos][0] <= frame:
            _frame, order, track, kind, rest = musical[pos]
            if kind == "on":
                midi_ch, note, velocity = rest
                if midi_ch == 9:
                    hit, duration = drum_hit(note)
                    data += hit
                    psg_mute[3 if note not in (45, 47, 48, 50) else 2] = frame + duration
                else:
                    key = (midi_ch, note, order)
                    voice = choose_voice(voices)
                    if voices[voice] is not None:
                        old = voices[voice]["key"]
                        active.pop(old, None)
                        data += key_off(voice)
                    voices[voice] = {"key": key, "note": note, "order": order}
                    active[key] = voice
                    data += key_off(voice)
                    data += set_note(voice, note)
                    data += key_on(voice)
            else:
                midi_ch, note = rest
                for key in [k for k in active if k[0] == midi_ch and k[1] == note]:
                    voice = active.pop(key)
                    if voices[voice] and voices[voice]["key"] == key:
                        voices[voice] = None
                        data += key_off(voice)
            pos += 1
        data.append(0x62)
        frame += 1

    for ch in range(6):
        data += key_off(ch)
    for ch in range(4):
        data += psg_volume(ch, 15)
    data.append(0x66)

    total_samples = frame * 735
    header = bytearray(0x100)
    header[0:4] = b"Vgm "
    struct.pack_into("<I", header, 0x08, 0x00000170)
    struct.pack_into("<I", header, 0x18, total_samples)
    struct.pack_into("<I", header, 0x1C, 0x100 + loop_data_offset - 0x1C)
    struct.pack_into("<I", header, 0x20, total_samples)
    struct.pack_into("<I", header, 0x24, 60)
    struct.pack_into("<I", header, 0x2C, 7670454)
    struct.pack_into("<I", header, 0x34, 0x100 - 0x34)
    out = header + data
    struct.pack_into("<I", out, 0x04, len(out) - 4)
    return out


def main():
    if len(sys.argv) != 3:
        print("usage: midi_to_fm_vgm.py input.mid output.vgm", file=sys.stderr)
        return 2
    open(sys.argv[2], "wb").write(build_vgm(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
