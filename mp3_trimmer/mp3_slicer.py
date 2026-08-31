"""Pure-Python MP3 frame parsing and lossless trimming.

The module walks the MPEG audio frame headers of an MP3 so a section can be cut
out on exact frame boundaries.  No re-encoding and no external tools (ffmpeg,
pydub, ...) are required.

Everything works on streams and never holds more than one chunk in memory, so
files of any size can be scanned and trimmed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator, List, Optional

CHUNK_SIZE = 1 << 20        # 1 MB read size
MAX_FRAME_SIZE = 4096       # every MPEG audio frame is far smaller than this

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
    """One MPEG audio frame inside the source."""

    offset: int
    length: int
    duration: float          # seconds
    start: float             # seconds from the first frame
    bitrate: int             # kbit/s
    sample_rate: int         # Hz

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass(frozen=True)
class Summary:
    """What a full scan of an MP3 tells us about it."""

    duration: float
    frames: int
    tag_size: int            # bytes of leading ID3v2 tag


@dataclass(frozen=True)
class Section:
    """The part that was actually written out."""

    start: float
    end: float
    size: int                # bytes written

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Slice(Section):
    """A section that was cut in memory, including its bytes."""

    data: bytes = b""


def _syncsafe(data: bytes) -> int:
    value = 0
    for byte in data:
        value = (value << 7) | (byte & 0x7F)
    return value


def id3v2_size(header: bytes) -> int:
    """Length of a leading ID3v2 tag, or 0 when there is none."""
    if len(header) < 10 or header[:3] != b"ID3":
        return 0
    size = 10 + _syncsafe(header[6:10])
    if header[5] & 0x10:  # footer present
        size += 10
    return size


def _parse_header(data: bytes, pos: int) -> Optional[Frame]:
    """Decode a frame header at ``pos`` or return None when it is not valid."""
    if pos + 4 > len(data):
        return None
    h1, h2 = data[pos + 1], data[pos + 2]
    if data[pos] != 0xFF or (h1 & 0xE0) != 0xE0:
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


def _is_info_frame(chunk: bytes) -> bool:
    """True for a Xing/Info/VBRI header frame (metadata, not audible audio)."""
    return b"Xing" in chunk[:40] or b"Info" in chunk[:40] or chunk[36:40] == b"VBRI"


def read_tag_size(stream: BinaryIO) -> int:
    """Read the ID3v2 tag length from the start of ``stream`` and rewind."""
    stream.seek(0)
    size = id3v2_size(stream.read(10))
    stream.seek(0)
    return size


def iter_frames(stream: BinaryIO, *, chunk_size: int = CHUNK_SIZE) -> Iterator[Frame]:
    """Yield every audio frame of ``stream`` in order, one chunk at a time.

    The frame data itself is not kept, so memory use stays flat no matter how
    long the file is.  ``Frame.offset`` is absolute within the stream.
    """
    for frame, _ in _iter_frames(stream, chunk_size=chunk_size, with_data=False):
        yield frame


def iter_frames_with_data(stream: BinaryIO,
                          *,
                          chunk_size: int = CHUNK_SIZE) -> Iterator[tuple[Frame, bytes]]:
    """Like :func:`iter_frames`, but also yields the bytes of each frame.

    Copying frames has to go through this: seeking the stream while
    :func:`iter_frames` is reading from it would corrupt its own buffer.
    """
    yield from _iter_frames(stream, chunk_size=chunk_size, with_data=True)


def _iter_frames(stream: BinaryIO,
                 *,
                 chunk_size: int,
                 with_data: bool) -> Iterator[tuple[Frame, bytes]]:
    tag_size = read_tag_size(stream)
    stream.seek(tag_size)

    buffer = b""
    base = tag_size     # absolute offset of buffer[0]
    pos = 0             # index into buffer
    elapsed = 0.0
    eof = False
    started = False

    while True:
        # Keep at least one whole frame in the buffer while there is more to read.
        # This has to loop: a chunk can be smaller than a frame.
        while not eof and len(buffer) - pos < MAX_FRAME_SIZE:
            chunk = stream.read(chunk_size)
            if chunk:
                buffer = buffer[pos:] + chunk
                base += pos
                pos = 0
            else:
                eof = True
        if pos >= len(buffer):
            return

        frame = _parse_header(buffer, pos)
        if frame is None:
            nxt = buffer.find(b"\xff", pos + 1)
            if nxt == -1:
                if eof:
                    return
                base += len(buffer)
                buffer, pos = b"", 0
                continue
            pos = nxt
            continue

        if not started:
            # Require a second valid frame right after, so that a stray 0xFF byte
            # inside a tag is not mistaken for the start of the audio.
            follower = _parse_header(buffer, pos + frame.length)
            if follower is None and not (eof and pos + frame.length >= len(buffer)):
                nxt = buffer.find(b"\xff", pos + 1)
                if nxt == -1:
                    if eof:
                        return
                    base += len(buffer)
                    buffer, pos = b"", 0
                    continue
                pos = nxt
                continue
            if _is_info_frame(buffer[pos:pos + frame.length]):
                pos += frame.length  # skip the VBR header frame
                continue

        started = True
        yield (
            Frame(
                offset=base + pos,
                length=frame.length,
                duration=frame.duration,
                start=elapsed,
                bitrate=frame.bitrate,
                sample_rate=frame.sample_rate,
            ),
            buffer[pos:pos + frame.length] if with_data else b"",
        )
        elapsed += frame.duration
        pos += frame.length


def scan(stream: BinaryIO, *, chunk_size: int = CHUNK_SIZE) -> Summary:
    """Walk the whole stream and report its playing time and frame count."""
    frames = 0
    elapsed = 0.0
    for frame in iter_frames(stream, chunk_size=chunk_size):
        frames += 1
        elapsed = frame.end
    if not frames:
        raise Mp3Error("No MPEG audio frames found - is this really an MP3 file?")
    return Summary(duration=elapsed, frames=frames, tag_size=read_tag_size(stream))


def scan_file(path: str | Path, *, chunk_size: int = CHUNK_SIZE) -> Summary:
    """Playing time and frame count of an MP3 on disk."""
    with open(path, "rb") as stream:
        return scan(stream, chunk_size=chunk_size)


def parse_frames(data: bytes) -> List[Frame]:
    """Every audio frame of an in-memory MP3."""
    return list(iter_frames(BytesIO(data)))


def duration(data: bytes) -> float:
    """Playing time of an in-memory MP3, in seconds."""
    return scan(BytesIO(data)).duration


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


def _check_range(start: float, end: float) -> None:
    if start < 0:
        raise ValueError("Start time cannot be negative")
    if end <= start:
        raise ValueError("End time must be later than the start time")


def slice_stream(source: BinaryIO,
                 target: BinaryIO,
                 start: float,
                 end: float,
                 *,
                 keep_tags: bool = True,
                 chunk_size: int = CHUNK_SIZE) -> Section:
    """Copy the frames of ``source`` between ``start`` and ``end`` into ``target``.

    Frames are copied verbatim, so the audio is never re-encoded.  Every frame
    that overlaps the window is kept, which is why the returned section can be
    slightly wider than the times asked for.
    """
    _check_range(start, end)

    written = 0
    if keep_tags:
        tag_size = read_tag_size(source)
        if tag_size:
            source.seek(0)
            remaining = tag_size
            while remaining > 0:
                chunk = source.read(min(chunk_size, remaining))
                if not chunk:
                    break
                target.write(chunk)
                written += len(chunk)
                remaining -= len(chunk)

    first: Optional[Frame] = None
    last: Optional[Frame] = None
    total = 0.0
    for frame, payload in iter_frames_with_data(source, chunk_size=chunk_size):
        total = frame.end
        if frame.end <= start:
            continue
        if frame.start >= end:
            break
        target.write(payload)
        written += frame.length
        if first is None:
            first = frame
        last = frame

    if total == 0.0:
        raise Mp3Error("No MPEG audio frames found - is this really an MP3 file?")
    if first is None or last is None:
        raise ValueError(
            f"The selected range holds no audio, the file is {format_timecode(total)} long"
        )
    return Section(start=first.start, end=last.end, size=written)


def slice_file(source: str | Path,
               target: str | Path,
               start: float,
               end: float,
               *,
               keep_tags: bool = True,
               chunk_size: int = CHUNK_SIZE) -> Section:
    """Trim an MP3 on disk into another file on disk."""
    with open(source, "rb") as src, open(target, "wb") as dst:
        return slice_stream(src, dst, start, end, keep_tags=keep_tags, chunk_size=chunk_size)


def slice_mp3(data: bytes, start: float, end: float, *, keep_tags: bool = True) -> Slice:
    """Trim an in-memory MP3 and return the result together with its bytes."""
    target = BytesIO()
    section = slice_stream(BytesIO(data), target, start, end, keep_tags=keep_tags)
    return Slice(start=section.start, end=section.end, size=section.size, data=target.getvalue())


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Trim a part out of an MP3 file.")
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("start", help="start time as 00:00:00")
    parser.add_argument("end", help="end time as 00:00:00")
    args = parser.parse_args()

    section = slice_file(
        args.source, args.destination, parse_timecode(args.start), parse_timecode(args.end)
    )
    print(
        f"Wrote {args.destination}: {format_timecode(section.start)} - "
        f"{format_timecode(section.end)} ({section.duration:.2f} s, {section.size} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
