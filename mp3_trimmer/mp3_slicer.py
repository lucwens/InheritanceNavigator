"""Pure-Python MP3 frame parsing and lossless trimming.

The module walks the MPEG audio frame headers of an MP3 file so a section can be
cut out on exact frame boundaries.  No re-encoding and no external tools
(ffmpeg, pydub, ...) are required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

# Bitrate tables in kbit/s.  Index 0 (free format) and 15 (invalid) are None.
_BITRATES = {
    # MPEG 1
    (1, 1): [None, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, None],
    (1, 2): [None, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, None],
    (1, 3): [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, None],
    # MPEG 2 / 2.5
    (2, 1): [None, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, None],
    (2, 2): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, None],
}
_BITRATES[(2, 3)] = _BITRATES[(2, 2)]

_SAMPLE_RATES = {
    1: [44100, 48000, 32000],      # MPEG 1
    2: [22050, 24000, 16000],      # MPEG 2
    25: [11025, 12000, 8000],      # MPEG 2.5
}

_SAMPLES_PER_FRAME = {
    (1, 1): 384, (1, 2): 1152, (1, 3): 1152,
    (2, 1): 384, (2, 2): 1152, (2, 3): 576,
}


class Mp3Error(ValueError):
    """Raised when the input is not usable MP3 audio."""


@dataclass(frozen=True)
class Frame:
    """One MPEG audio frame inside the source buffer."""

    offset: int
    length: int
    duration: float          # seconds
    start: float             # seconds from the first frame
    bitrate: int             # kbit/s
    sample_rate: int         # Hz

    @property
    def end(self) -> float:
        return self.start + self.duration


def _syncsafe(data: bytes) -> int:
    value = 0
    for byte in data:
        value = (value << 7) | (byte & 0x7F)
    return value


def id3v2_size(data: bytes) -> int:
    """Length of a leading ID3v2 tag, or 0 when there is none."""
    if len(data) < 10 or data[:3] != b"ID3":
        return 0
    flags = data[5]
    size = 10 + _syncsafe(data[6:10])
    if flags & 0x10:  # footer present
        size += 10
    return size


def _parse_header(data: bytes, pos: int) -> Optional[Frame]:
    """Decode a frame header at ``pos`` or return None when it is not valid."""
    if pos + 4 > len(data):
        return None
    h0, h1, h2, h3 = data[pos], data[pos + 1], data[pos + 2], data[pos + 3]
    if h0 != 0xFF or (h1 & 0xE0) != 0xE0:
        return None

    version_bits = (h1 >> 3) & 0x03
    if version_bits == 0x01:  # reserved
        return None
    version = {0x00: 25, 0x02: 2, 0x03: 1}[version_bits]

    layer_bits = (h1 >> 1) & 0x03
    if layer_bits == 0x00:  # reserved
        return None
    layer = {0x01: 3, 0x02: 2, 0x03: 1}[layer_bits]

    table_version = 1 if version == 1 else 2
    bitrate = _BITRATES[(table_version, layer)][(h2 >> 4) & 0x0F]
    if bitrate is None:  # free format or invalid
        return None

    sample_rate_index = (h2 >> 2) & 0x03
    if sample_rate_index == 0x03:
        return None
    sample_rate = _SAMPLE_RATES[version][sample_rate_index]

    padding = (h2 >> 1) & 0x01
    samples = _SAMPLES_PER_FRAME[(table_version, layer)]

    if layer == 1:
        length = (12 * bitrate * 1000 // sample_rate + padding) * 4
    else:
        length = (samples // 8) * bitrate * 1000 // sample_rate + padding

    if length <= 4 or pos + length > len(data):
        return None

    return Frame(
        offset=pos,
        length=length,
        duration=samples / sample_rate,
        start=0.0,
        bitrate=bitrate,
        sample_rate=sample_rate,
    )


def _is_info_frame(data: bytes, frame: Frame) -> bool:
    """True for a Xing/Info/VBRI header frame (metadata, not audible audio)."""
    chunk = data[frame.offset:frame.offset + frame.length]
    return b"Xing" in chunk[:40] or b"Info" in chunk[:40] or chunk[36:40] == b"VBRI"


def parse_frames(data: bytes) -> List[Frame]:
    """Return every audio frame of ``data``, in order, with cumulative times."""
    pos = id3v2_size(data)
    frames: List[Frame] = []
    elapsed = 0.0
    size = len(data)

    while pos < size - 3:
        frame = _parse_header(data, pos)
        if frame is None:
            # Not a frame here: jump to the next possible sync word.
            nxt = data.find(b"\xff", pos + 1)
            if nxt == -1:
                break
            pos = nxt
            continue

        if not frames:
            # Require a second valid frame right after so that random 0xFF bytes
            # in a tag are not mistaken for the start of the audio.
            follower = _parse_header(data, pos + frame.length)
            if follower is None and pos + frame.length < size - 3:
                nxt = data.find(b"\xff", pos + 1)
                if nxt == -1:
                    break
                pos = nxt
                continue

        if not frames and _is_info_frame(data, frame):
            pos += frame.length  # skip the VBR header frame
            continue

        frames.append(
            Frame(
                offset=frame.offset,
                length=frame.length,
                duration=frame.duration,
                start=elapsed,
                bitrate=frame.bitrate,
                sample_rate=frame.sample_rate,
            )
        )
        elapsed += frame.duration
        pos += frame.length

    return frames


def duration(data: bytes) -> float:
    """Playing time of the MP3 in seconds."""
    frames = parse_frames(data)
    if not frames:
        raise Mp3Error("No MPEG audio frames found - is this really an MP3 file?")
    return frames[-1].end


def parse_timecode(text: str) -> float:
    """Parse ``HH:MM:SS`` (also ``MM:SS``, ``SS`` and fractional seconds)."""
    value = (text or "").strip()
    if not value:
        raise ValueError("Time is empty, use 00:00:00")
    if not re.fullmatch(r"\d+(:\d{1,2}){0,2}(\.\d+)?", value):
        raise ValueError(f"'{text}' is not a valid time, use 00:00:00")

    parts = value.split(":")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    if len(parts) > 1 and any(float(p) >= 60 for p in parts[1:]):
        raise ValueError(f"'{text}' is not a valid time, minutes and seconds must be below 60")
    return seconds


def format_timecode(seconds: float) -> str:
    """Format seconds as ``HH:MM:SS``."""
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


@dataclass(frozen=True)
class Slice:
    """The trimmed MP3 plus the exact section that was cut."""

    data: bytes
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def slice_mp3(data: bytes, start: float, end: float, keep_tags: bool = True) -> Slice:
    """Cut ``data`` between ``start`` and ``end`` (seconds) on frame boundaries."""
    if start < 0:
        raise ValueError("Start time cannot be negative")
    if end <= start:
        raise ValueError("End time must be later than the start time")

    frames = parse_frames(data)
    if not frames:
        raise Mp3Error("No MPEG audio frames found - is this really an MP3 file?")

    total = frames[-1].end
    if start >= total:
        raise ValueError(f"Start time is past the end of the file ({format_timecode(total)})")

    # Keep every frame that overlaps the requested window.
    selected = [f for f in frames if f.end > start and f.start < end]
    if not selected:
        raise ValueError("The selected range does not contain any audio")

    chunks = []
    if keep_tags:
        tag = id3v2_size(data)
        if tag:
            chunks.append(data[:tag])
    for frame in selected:
        chunks.append(data[frame.offset:frame.offset + frame.length])

    return Slice(data=b"".join(chunks), start=selected[0].start, end=selected[-1].end)


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Trim a part out of an MP3 file.")
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("start", help="start time as 00:00:00")
    parser.add_argument("end", help="end time as 00:00:00")
    args = parser.parse_args()

    with open(args.source, "rb") as handle:
        data = handle.read()

    result = slice_mp3(data, parse_timecode(args.start), parse_timecode(args.end))
    with open(args.destination, "wb") as handle:
        handle.write(result.data)

    print(
        f"Wrote {args.destination}: {format_timecode(result.start)} - "
        f"{format_timecode(result.end)} ({result.duration:.2f} s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
