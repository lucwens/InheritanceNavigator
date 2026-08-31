"""NiceGUI app: drop an MP3, give a start and end time, download the trimmed part.

Run with:  python app.py
Then open http://localhost:8080 in a browser.

Uploads are streamed to a temporary file and trimmed straight from there, so
the size of the MP3 is not limited by the memory of the machine.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from nicegui import app, events, run, ui

from mp3_slicer import (
    Mp3Error,
    Summary,
    format_timecode,
    parse_timecode,
    scan_file,
    slice_file,
)

# Quasar refuses files before they are even sent; these are the checks it makes.
REJECTION_REASONS = {
    "accept": "the file is not an MP3 - its name has to end in .mp3",
    "max-file-size": "the file is too large",
    "max-total-size": "the files are too large together",
    "max-files": "only one file at a time - clear the list first",
    "duplicate": "that file is already in the list",
    "filter": "the file was filtered out",
}


def format_size(num_bytes: int) -> str:
    """Human readable file size."""
    size = float(num_bytes)
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in ("B", "kB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


@dataclass
class Session:
    """Everything the page knows about the file the user dropped."""

    workdir: Path
    name: str = ""
    source: Optional[Path] = None
    summary: Optional[Summary] = field(default=None, repr=False)

    @property
    def loaded(self) -> bool:
        return self.source is not None and self.summary is not None

    @property
    def length(self) -> float:
        return self.summary.duration if self.summary else 0.0

    @property
    def trimmed_name(self) -> str:
        stem = Path(self.name).stem or "audio"
        return f"{stem}_trimmed.mp3"


@ui.page("/")
def main_page() -> None:
    session = Session(workdir=Path(tempfile.mkdtemp(prefix="mp3_trimmer_")))
    ui.context.client.on_disconnect(lambda: shutil.rmtree(session.workdir, ignore_errors=True))

    with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
        ui.label("MP3 Trimmer").classes("text-3xl font-bold")
        ui.label("Drop an MP3 file, choose a start and end time, and save that part.") \
            .classes("text-gray-600")

        upload = ui.upload(
            label="Drop your MP3 here or click to browse",
            auto_upload=True,
            max_files=1,
            on_upload=lambda e: load_file(e),
        ).props('accept=".mp3,audio/mpeg,audio/mp3" flat bordered').classes("w-full")
        # NiceGUI's own on_rejected drops the payload, so listen to Quasar directly
        # to learn which check failed.
        upload.on("rejected", lambda e: report_rejection(e), args=None)

        with ui.row().classes("items-center gap-2"):
            spinner = ui.spinner(size="sm")
            spinner.set_visibility(False)
            file_label = ui.label("No file loaded yet.").classes("text-sm text-gray-500")

        with ui.card().classes("w-full") as editor:
            ui.label("Select the part to keep").classes("text-lg font-medium")
            with ui.row().classes("w-full gap-4 items-start"):
                start_input = ui.input("Start (00:00:00)", value="00:00:00") \
                    .props("mask='##:##:##' outlined").classes("flex-1")
                end_input = ui.input("End (00:00:00)", value="00:00:00") \
                    .props("mask='##:##:##' outlined").classes("flex-1")
            with ui.row().classes("gap-2"):
                trim_button = ui.button("Save trimmed MP3", icon="content_cut",
                                        on_click=lambda: trim())
                ui.button("Reset times", on_click=lambda: reset_times()).props("flat")
            result_label = ui.label("").classes("text-sm text-gray-600")
        editor.set_visibility(False)

        audio_preview = ui.audio("").classes("w-full")
        audio_preview.set_visibility(False)

    def report_rejection(event: events.GenericEventArguments) -> None:
        # Quasar sends a list of {failedPropValidation, file} entries; depending on
        # the NiceGUI version it arrives as that list or wrapped in another one.
        raw = event.args if isinstance(event.args, list) else [event.args]
        entries = [item for entry in raw for item in (entry if isinstance(entry, list) else [entry])]
        reasons = {
            REJECTION_REASONS.get(entry.get("failedPropValidation", ""), "the file was rejected")
            for entry in entries
            if isinstance(entry, dict)
        }
        detail = " and ".join(sorted(reasons)) or "the file was rejected"
        ui.notify(f"Cannot use this file: {detail}.", type="negative", timeout=8000)
        upload.reset()

    async def load_file(event: events.UploadEventArguments) -> None:
        name = event.file.name
        source = session.workdir / "source.mp3"
        spinner.set_visibility(True)
        file_label.set_text(f"Reading {name} ...")
        try:
            await event.file.save(source)  # streamed, never held in memory
            summary = await run.cpu_bound(scan_file, source)
        except Mp3Error as error:
            session.name, session.source, session.summary = "", None, None
            editor.set_visibility(False)
            audio_preview.set_visibility(False)
            file_label.set_text(f"Could not read {name}: {error}")
            ui.notify(str(error), type="negative", timeout=8000)
            return
        finally:
            spinner.set_visibility(False)
            upload.reset()

        session.name, session.source, session.summary = name, source, summary
        file_label.set_text(
            f"{name} - {format_timecode(summary.duration)} "
            f"({format_size(source.stat().st_size)}, {summary.frames} frames)"
        )
        reset_times()
        editor.set_visibility(True)
        result_label.set_text("")
        audio_preview.set_visibility(False)

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

    async def trim() -> None:
        if not session.loaded:
            ui.notify("Drop an MP3 file first.", type="warning")
            return
        times = read_times()
        if times is None:
            return

        target = session.workdir / session.trimmed_name
        trim_button.disable()
        spinner.set_visibility(True)
        try:
            section = await run.cpu_bound(slice_file, session.source, target, *times)
        except (ValueError, Mp3Error) as error:
            ui.notify(str(error), type="negative", timeout=8000)
            return
        finally:
            trim_button.enable()
            spinner.set_visibility(False)

        # Serve the result from disk, so even a long excerpt is streamed, not
        # squeezed through a data URL.
        audio_preview.set_source(app.add_media_file(local_file=target))
        audio_preview.set_visibility(True)
        result_label.set_text(
            f"Saved {session.trimmed_name}: {format_timecode(section.start)} - "
            f"{format_timecode(section.end)} ({section.duration:.2f} s, "
            f"{format_size(section.size)})"
        )
        ui.download.file(target, session.trimmed_name, "audio/mpeg")
        ui.notify(f"Saved {session.trimmed_name}", type="positive")


def run_app() -> None:
    parser = argparse.ArgumentParser(description="NiceGUI MP3 trimmer.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args()

    # Same worker start method everywhere (it is already the default on Windows),
    # so behaviour does not depend on the platform.
    run.process_pool_start_method = "spawn"
    ui.run(
        host=args.host,
        port=args.port,
        title="MP3 Trimmer",
        show=not args.no_browser,
        reload=False,
    )


if __name__ == "__main__":
    # Deliberately not "__mp_main__": run.cpu_bound spawns worker processes that
    # import this module, and they must not start a second server.
    run_app()
