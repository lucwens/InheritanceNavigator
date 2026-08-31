"""NiceGUI app: drop an MP3, give a start and end time, download the trimmed part.

Run with:  python app.py
Then open http://localhost:8080 in a browser.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from nicegui import events, ui

from mp3_slicer import (
    Mp3Error,
    format_timecode,
    duration as mp3_duration,
    parse_timecode,
    slice_mp3,
)

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


@dataclass
class Session:
    """Everything the page knows about the file the user dropped."""

    name: str = ""
    data: bytes = field(default=b"", repr=False)
    length: float = 0.0

    @property
    def loaded(self) -> bool:
        return bool(self.data)

    @property
    def trimmed_name(self) -> str:
        stem = Path(self.name).stem or "audio"
        return f"{stem}_trimmed.mp3"


@ui.page("/")
def main_page() -> None:
    session = Session()

    with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
        ui.label("MP3 Trimmer").classes("text-3xl font-bold")
        ui.label("Drop an MP3 file, choose a start and end time, and save that part.") \
            .classes("text-gray-600")

        upload = ui.upload(
            label="Drop your MP3 here or click to browse",
            auto_upload=True,
            max_files=1,
            max_file_size=MAX_FILE_SIZE,
            on_upload=lambda e: load_file(e),
            on_rejected=lambda _: ui.notify(
                f"File rejected - only one MP3 up to {MAX_FILE_SIZE // 1024 // 1024} MB is accepted.",
                type="negative",
            ),
        ).props('accept=".mp3,audio/mpeg" flat bordered').classes("w-full")

        file_label = ui.label("No file loaded yet.").classes("text-sm text-gray-500")

        with ui.card().classes("w-full") as editor:
            ui.label("Select the part to keep").classes("text-lg font-medium")
            with ui.row().classes("w-full gap-4 items-start"):
                start_input = ui.input("Start (00:00:00)", value="00:00:00") \
                    .props("mask='##:##:##' outlined").classes("flex-1")
                end_input = ui.input("End (00:00:00)", value="00:00:00") \
                    .props("mask='##:##:##' outlined").classes("flex-1")
            with ui.row().classes("gap-2"):
                ui.button("Save trimmed MP3", icon="content_cut", on_click=lambda: trim())
                ui.button("Reset times", on_click=lambda: reset_times()).props("flat")
            result_label = ui.label("").classes("text-sm text-gray-600")
        editor.set_visibility(False)

        audio_preview = ui.audio("").classes("w-full")
        audio_preview.set_visibility(False)

    async def load_file(event: events.UploadEventArguments) -> None:
        name = event.file.name
        data = await event.file.read()
        try:
            length = mp3_duration(data)
        except Mp3Error as error:
            session.name, session.data, session.length = "", b"", 0.0
            editor.set_visibility(False)
            audio_preview.set_visibility(False)
            file_label.set_text(f"Could not read {name}: {error}")
            ui.notify(str(error), type="negative")
            return

        session.name, session.data, session.length = name, data, length
        file_label.set_text(
            f"{name} - {format_timecode(length)} ({len(data) / 1024 / 1024:.1f} MB)"
        )
        reset_times()
        editor.set_visibility(True)
        result_label.set_text("")
        upload.reset()

    def reset_times() -> None:
        start_input.value = "00:00:00"
        end_input.value = format_timecode(session.length)

    def read_times() -> Optional[tuple[float, float]]:
        try:
            start = parse_timecode(start_input.value)
            end = parse_timecode(end_input.value)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return None
        if end > session.length:
            end = session.length
            end_input.value = format_timecode(end)
            ui.notify("End time was past the end of the file, clamped to the last frame.",
                      type="warning")
        if end <= start:
            ui.notify("The end time must be later than the start time.", type="negative")
            return None
        return start, end

    def trim() -> None:
        if not session.loaded:
            ui.notify("Drop an MP3 file first.", type="warning")
            return
        times = read_times()
        if times is None:
            return

        try:
            result = slice_mp3(session.data, *times)
        except (ValueError, Mp3Error) as error:
            ui.notify(str(error), type="negative")
            return

        audio_preview.set_source(
            "data:audio/mpeg;base64," + base64.b64encode(result.data).decode()
        )
        audio_preview.set_visibility(True)
        result_label.set_text(
            f"Saved {session.trimmed_name}: {format_timecode(result.start)} - "
            f"{format_timecode(result.end)} ({result.duration:.2f} s, "
            f"{len(result.data) / 1024:.0f} kB)"
        )
        ui.download.content(result.data, session.trimmed_name, "audio/mpeg")
        ui.notify(f"Saved {session.trimmed_name}", type="positive")


def run() -> None:
    parser = argparse.ArgumentParser(description="NiceGUI MP3 trimmer.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args()

    ui.run(
        host=args.host,
        port=args.port,
        title="MP3 Trimmer",
        show=not args.no_browser,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
