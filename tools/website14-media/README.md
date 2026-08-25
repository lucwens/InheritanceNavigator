# Task 482 — website 14 media

`ctech_media.py` reads the originals from your mounted Drive folder, converts
them to web-sized WebP, then creates the Odoo attachments and writes the
`<img>` / `<video>` snippets for the page views.

Nothing has to be transferred — the source images are already on your machine
at `G:\My Drive\C-Tech\Marketing\Websters\Media`.

## Run

```bash
pip install pillow imageio-ffmpeg

# 1. convert — no network, no credentials
python ctech_media.py convert

# 2. prune — open website14-media/_contact-sheets/ and delete the WebP files
#    you don't want from website14-media/<folder>/

# 3. upload whatever survived
python ctech_media.py upload --url https://<you>.odoo.com \
    --db <db> --user <you>@ctechmetrology.com --api-key <key>
```

If your Drive letter differs: `python ctech_media.py convert --media "D:\...\Media"`.

`upload` is safe to re-run: it fetches the names already on website 14 in one
call, skips those, and only sends what is new — so an interrupted run just
picks up where it stopped. Files you deleted in step 2 are skipped too.
`manifest.json` is flushed every 10 uploads, so a crash never loses progress.

Odoo Online rate-limits XML-RPC. The script sends one write per file, pauses
`--delay` seconds (0.4 by default) between them, and backs off and retries on
a 429. Raise the delay if you still get throttled:

```bash
python ctech_media.py upload --delay 1.0 --url ... --db ... --user ... --api-key ...
```

Use `--force` to re-send files that are already up there (after re-converting
at different settings, say).

## What it produces

```
website14-media/
  _contact-sheets/   labelled thumbnail grids, 30 per sheet — prune from these
  closure/       41 → /automotive          (closure section)
  suspension/    15 → /automotive          (deformation section)
  robotics/      83 → /robotics
  towing/        39 → /maritime-offshore
  structural/   113 → /civil-engineering
  video/          2 → /automotive          (closure section)
  manifest.json      every file mapped back to its Drive original
  snippets.html      written by 'upload', with the live attachment URLs
```

291 images + 2 clips, ~42 MB total out of ~450 MB of originals.
`/aerospace` is untouched — there is no photography for it in the Media folder.

Attachments are created with `website_id=14`, `public=True`,
`res_model='ir.ui.view'`, which is what Odoo's own website media dialog uses.

## Conversion rules

- Max 1600 px wide, WebP quality 82, never upscaled.
- EXIF orientation baked in, so nothing arrives rotated.
- All BMPs and TIFFs converted — the Hexapod series, `SMB.bmp`, the towing-tank
  CAD set, `F18.bmp`, `Picture from RUAG.bmp`, both `.tif` files.
- Sources under 40 KB skipped: the `*-400px.jpg` set, `trunc.jpg`, the
  `01010xxx.JPG` set, `MVC-650S/651S/652S.JPG`, `UX150.bmp`. All are 1998–2005
  web thumbnails well under 500 px — unusable at any size the site needs.
- Exact duplicates dropped by MD5.
- The two closure clips (`doorslam.avi`, `cabrio roof SLK.avi`) encoded to
  muted H.264 with `+faststart` and a poster still. Both sources have no audio
  track at all. They are CTrack replays — the door as a CAD model swinging on
  its hinge with the tracked markers on it — which shows the measurement more
  clearly than camera footage would.
- Skipped as stock, licence unclear: both `shutterstock_*.jpg`, and
  `sports car rear suspension - is denk ik een Shutterstock beeld.jpg`
  (its Drive description credits `© John Marian/Transtock/Corbis`).
  Remove them from `SKIP` at the top of the script if you want them anyway.

## Before the snippets go live

`alt` is filled from the original filename, which is a placeholder, not real
alt text. Write a proper one-line description for each image you actually keep
before pasting the snippet into a page view.
