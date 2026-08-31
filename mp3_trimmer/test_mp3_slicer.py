"""Tests for the MP3 slicer, using synthetic MPEG-1 Layer III frames."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from mp3_slicer import (
    Mp3Error,
    format_timecode,
    duration,
    iter_frames,
    parse_frames,
    parse_timecode,
    scan,
    scan_file,
    slice_file,
    slice_mp3,
)

# MPEG-1 Layer III, 128 kbit/s, 44100 Hz, no padding, stereo.
FRAME_HEADER = bytes([0xFF, 0xFB, 0x90, 0x00])
FRAME_LENGTH = 144 * 128000 // 44100          # 417 bytes
FRAME_DURATION = 1152 / 44100                 # ~0.0261 s


def make_frame(filler: int = 0) -> bytes:
    return FRAME_HEADER + bytes([filler]) * (FRAME_LENGTH - 4)


def make_mp3(frame_count: int, tag: bytes = b"") -> bytes:
    return tag + b"".join(make_frame(i % 251) for i in range(frame_count))


def id3v2_tag(payload_size: int = 100) -> bytes:
    size = bytes([0, 0, (payload_size >> 7) & 0x7F, payload_size & 0x7F])
    return b"ID3\x03\x00\x00" + size + b"\x00" * payload_size


class TimecodeTests(unittest.TestCase):
    def test_parses_hh_mm_ss(self):
        self.assertEqual(parse_timecode("00:00:00"), 0)
        self.assertEqual(parse_timecode("00:01:30"), 90)
        self.assertEqual(parse_timecode("01:02:03"), 3723)

    def test_parses_short_and_fractional_forms(self):
        self.assertEqual(parse_timecode("90"), 90)
        self.assertEqual(parse_timecode("2:05"), 125)
        self.assertAlmostEqual(parse_timecode("00:00:01.5"), 1.5)

    def test_rejects_nonsense(self):
        for value in ["", "abc", "1:2:3:4", "00:75:00", "-5"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_timecode(value)

    def test_formats_seconds(self):
        self.assertEqual(format_timecode(0), "00:00:00")
        self.assertEqual(format_timecode(3723), "01:02:03")


class ParseTests(unittest.TestCase):
    def test_finds_every_frame(self):
        frames = parse_frames(make_mp3(10))
        self.assertEqual(len(frames), 10)
        self.assertEqual(frames[0].length, FRAME_LENGTH)
        self.assertEqual(frames[0].bitrate, 128)
        self.assertEqual(frames[0].sample_rate, 44100)
        self.assertAlmostEqual(frames[3].start, 3 * FRAME_DURATION)

    def test_skips_id3v2_tag(self):
        frames = parse_frames(make_mp3(5, tag=id3v2_tag()))
        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[0].offset, 110)

    def test_duration(self):
        self.assertAlmostEqual(duration(make_mp3(100)), 100 * FRAME_DURATION)

    def test_rejects_non_mp3(self):
        with self.assertRaises(Mp3Error):
            duration(b"this is not audio" * 100)


class StreamingTests(unittest.TestCase):
    """The parser must give the same answer whatever the read size is."""

    def test_chunk_size_does_not_change_the_result(self):
        source = make_mp3(300, tag=id3v2_tag())
        reference = [(f.offset, f.length) for f in parse_frames(source)]
        for chunk_size in (64, 417, 1000, 4096, 1 << 20):
            with self.subTest(chunk_size=chunk_size):
                frames = list(iter_frames(BytesIO(source), chunk_size=chunk_size))
                self.assertEqual([(f.offset, f.length) for f in frames], reference)

    def test_frames_are_not_kept_in_memory(self):
        frames = iter_frames(BytesIO(make_mp3(10)))
        self.assertFalse(isinstance(frames, list))
        self.assertEqual(next(frames).offset, 0)

    def test_scan_reports_frames_and_tag(self):
        summary = scan(BytesIO(make_mp3(42, tag=id3v2_tag())))
        self.assertEqual(summary.frames, 42)
        self.assertEqual(summary.tag_size, 110)
        self.assertAlmostEqual(summary.duration, 42 * FRAME_DURATION)

    def test_trailing_partial_frame_is_ignored(self):
        source = make_mp3(20) + FRAME_HEADER + b"\x00" * 50  # cut off mid-frame
        self.assertEqual(len(parse_frames(source)), 20)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.source = self.dir / "source.mp3"
        self.source.write_bytes(make_mp3(400, tag=id3v2_tag()))

    def test_scan_file(self):
        summary = scan_file(self.source)
        self.assertEqual(summary.frames, 400)
        self.assertAlmostEqual(summary.duration, 400 * FRAME_DURATION)

    def test_slice_file_matches_in_memory_slice(self):
        target = self.dir / "out.mp3"
        section = slice_file(self.source, target, 1.0, 3.0)
        expected = slice_mp3(self.source.read_bytes(), 1.0, 3.0)
        self.assertEqual(target.read_bytes(), expected.data)
        self.assertEqual(section.size, target.stat().st_size)
        self.assertAlmostEqual(section.duration, 2.0, delta=2 * FRAME_DURATION)

    def test_slice_file_across_chunk_boundaries(self):
        target = self.dir / "small_chunks.mp3"
        section = slice_file(self.source, target, 2.0, 4.0, chunk_size=100)
        reference = slice_mp3(self.source.read_bytes(), 2.0, 4.0)
        self.assertEqual(target.read_bytes(), reference.data)
        self.assertAlmostEqual(section.start, reference.start)


class SliceTests(unittest.TestCase):
    def test_cuts_requested_window(self):
        source = make_mp3(200)
        result = slice_mp3(source, 1.0, 2.0)
        self.assertLessEqual(result.start, 1.0)
        self.assertGreaterEqual(result.end, 2.0)
        self.assertAlmostEqual(result.duration, 1.0, delta=2 * FRAME_DURATION)
        self.assertAlmostEqual(duration(result.data), result.duration, places=6)

    def test_output_is_frame_aligned_and_smaller(self):
        source = make_mp3(200)
        result = slice_mp3(source, 0.5, 1.5)
        self.assertEqual(len(result.data) % FRAME_LENGTH, 0)
        self.assertLess(len(result.data), len(source))

    def test_keeps_id3v2_tag_when_asked(self):
        source = make_mp3(50, tag=id3v2_tag())
        self.assertTrue(slice_mp3(source, 0, 0.5).data.startswith(b"ID3"))
        self.assertFalse(slice_mp3(source, 0, 0.5, keep_tags=False).data.startswith(b"ID3"))

    def test_full_range_returns_all_audio(self):
        source = make_mp3(30)
        result = slice_mp3(source, 0, duration(source))
        self.assertEqual(len(result.data), 30 * FRAME_LENGTH)

    def test_rejects_bad_ranges(self):
        source = make_mp3(30)
        with self.assertRaises(ValueError):
            slice_mp3(source, 2, 1)
        with self.assertRaises(ValueError):
            slice_mp3(source, -1, 1)
        with self.assertRaises(ValueError):
            slice_mp3(source, 60, 70)


if __name__ == "__main__":
    unittest.main()
