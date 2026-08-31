# MP3 Trimmer

A small [NiceGUI](https://nicegui.io) app: drop an MP3 file in the browser, type a
start and an end time as `00:00:00`, and save that part of the file.

## Install and run

```bash
pip install -r requirements.txt
python app.py
```

The app opens on <http://localhost:8080>. Options: `--port`, `--host`,
`--no-browser`.

## Using it

1. Drag an MP3 onto the drop zone (or click it to browse). The file name and
   total playing time appear once it is read.
2. The start time defaults to `00:00:00` and the end time to the end of the
   file. Both fields take `HH:MM:SS`; `MM:SS`, plain seconds and fractions such
   as `00:00:01.5` are accepted too.
3. Press **Save trimmed MP3**. The browser downloads `<name>_trimmed.mp3` and a
   player appears so you can check the result.

## Command line

The trimming logic is usable without the UI:

```bash
python mp3_slicer.py song.mp3 excerpt.mp3 00:01:30 00:02:15
```

## How the trimming works

`mp3_slicer.py` walks the MPEG audio frame headers itself, so there are no
dependencies beyond NiceGUI — no ffmpeg, no pydub. It supports MPEG 1, 2 and 2.5,
layers I–III, constant and variable bitrate, and skips a leading ID3v2 tag and
any Xing/Info/VBRI header frame.

Every frame that overlaps the requested window is copied verbatim, so the audio
is never re-encoded and no quality is lost. The cut therefore lands on a frame
boundary: up to about 26 ms (one frame at 44.1 kHz) may be included on either
side of the times you type. The exact section that was written is reported under
the buttons. Because layer III frames may borrow from the bit reservoir of their
predecessor, the very first frames after a cut can sound slightly muted — the
same trade-off any lossless MP3 cutter makes.

## Tests

```bash
python -m unittest test_mp3_slicer -v
```
