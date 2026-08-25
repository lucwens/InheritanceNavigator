#!/usr/bin/env python3
"""
Task 482 - website 14 media.

Reads the originals straight from your mounted Drive folder, converts them to
web-sized WebP, then creates the Odoo attachments and emits the <img> snippets.

    pip install pillow imageio-ffmpeg

    # 1. convert (no network, no credentials)
    python ctech_media.py convert

    # 2. look at website14-media/_contact-sheets/, delete what you don't want

    # 3. upload what survived
    python ctech_media.py upload --url https://xxx.odoo.com \
        --db mydb --user me@ctechmetrology.com --api-key KEY

Re-running upload updates existing attachments instead of duplicating them.
"""
import argparse, base64, hashlib, json, math, os, re, sys, xmlrpc.client

MEDIA = r"G:\My Drive\C-Tech\Marketing\Websters\Media"
OUT = "website14-media"
WEBSITE_ID = 14
MAXW, QUALITY = 1600, 82
MIN_BYTES = 40_000          # below this the source is a 400px-era thumbnail

# Drive folder -> (output folder, website page, section)
FOLDERS = {
    "Closure testing":    ("closure",    "/automotive",        "closure"),
    "Suspension testing": ("suspension", "/automotive",        "deformation"),
    "Robotics":           ("robotics",   "/robotics",          ""),
    "Towing tanks":       ("towing",     "/maritime-offshore", ""),
    "Structural testing": ("structural", "/civil-engineering", ""),
}

# stock imagery - licence unclear, left out on purpose
SKIP = {
    "shutterstock_61875832.jpg",
    "shutterstock_81534238.jpg",
    "sports car rear suspension - is denk ik een Shutterstock beeld.jpg",
}

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif"}

# the two closure clips worth having, and how long to keep
CLIPS = {
    "doorslam.avi":       ("closure-testing-doorslam",
                           "Measured 3D replay of a car door swinging shut, "
                           "with its tracked markers"),
    "cabrio roof SLK.avi": ("closure-testing-slk-cabrio-roof",
                           "Measured 3D replay of a folding hardtop roof opening"),
}


def slug(name):
    s = os.path.splitext(name)[0].lower()
    for a, b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "image"


# --------------------------------------------------------------------- convert

def convert(media_root):
    from PIL import Image, ImageOps

    if not os.path.isdir(media_root):
        sys.exit(f"Media folder not found: {media_root}\n"
                 f"Pass the right path with --media.")

    manifest, seen, stats = [], {}, {}
    for drive_name, (folder, page, section) in FOLDERS.items():
        src_dir = os.path.join(media_root, drive_name)
        if not os.path.isdir(src_dir):
            print(f"  ! missing folder, skipped: {drive_name}")
            continue
        dst_dir = os.path.join(OUT, folder)
        os.makedirs(dst_dir, exist_ok=True)
        kept = skipped = 0

        for name in sorted(os.listdir(src_dir)):
            src = os.path.join(src_dir, name)
            if not os.path.isfile(src):
                continue
            if name in SKIP or os.path.splitext(name)[1].lower() not in IMG_EXT:
                continue
            if os.path.getsize(src) < MIN_BYTES:
                skipped += 1
                continue
            digest = hashlib.md5(open(src, "rb").read()).hexdigest()
            if digest in seen:                     # exact duplicate
                skipped += 1
                continue
            seen[digest] = name
            try:
                im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
            except Exception as e:
                print(f"  ! could not read {name}: {e}")
                continue
            w0, h0 = im.size
            if w0 > MAXW:                          # never upscale
                im = im.resize((MAXW, round(h0 * MAXW / w0)), Image.LANCZOS)
            out = os.path.join(dst_dir, f"{folder}-{slug(name)}.webp")
            im.save(out, "WEBP", quality=QUALITY, method=6)
            manifest.append(dict(source=name, folder=folder,
                                 file=os.path.relpath(out, OUT).replace("\\", "/"),
                                 page=page, section=section,
                                 alt=os.path.splitext(name)[0],
                                 web_px=f"{im.size[0]}x{im.size[1]}",
                                 web_kb=round(os.path.getsize(out) / 1024, 1),
                                 mimetype="image/webp"))
            kept += 1
        stats[folder] = (kept, skipped)
        print(f"  {folder:12s} -> {page:20s} {kept:4d} kept, {skipped:3d} skipped")

    manifest += convert_clips(media_root)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    contact_sheets(manifest)
    total_kb = sum(m["web_kb"] for m in manifest)
    print(f"\n{len(manifest)} files, {total_kb/1024:.1f} MB in ./{OUT}/")
    print(f"Review ./{OUT}/_contact-sheets/, delete what you don't want, then run "
          f"'upload'.")


def convert_clips(media_root):
    """Encode the two closure clips to muted web MP4 + poster. Optional."""
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        print("  ! imageio-ffmpeg not installed, skipping the two video clips")
        return []
    import subprocess
    out_dir = os.path.join(OUT, "video")
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for fname, (base, alt) in CLIPS.items():
        src = os.path.join(media_root, "Closure testing", fname)
        if not os.path.isfile(src):
            print(f"  ! clip not found, skipped: {fname}")
            continue
        mp4 = os.path.join(out_dir, base + ".mp4")
        poster = os.path.join(out_dir, base + "-poster.webp")
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        subprocess.run([ff, "-loglevel", "error", "-y", "-i", src, "-an",
                        "-vf", vf + ",format=yuv420p", "-c:v", "libx264",
                        "-preset", "slow", "-crf", "24", "-profile:v", "high",
                        "-movflags", "+faststart", mp4], check=True)
        subprocess.run([ff, "-loglevel", "error", "-y", "-ss", "1", "-i", src,
                        "-frames:v", "1", "-vf", vf, "-c:v", "libwebp",
                        "-quality", "82", poster], check=True)
        rows.append(dict(source=fname, folder="closure",
                         file=f"video/{base}.mp4", page="/automotive",
                         section="closure", alt=alt, web_px="752x420",
                         web_kb=round(os.path.getsize(mp4) / 1024, 1),
                         kind="video", mimetype="video/mp4",
                         poster_file=f"video/{base}-poster.webp"))
        print(f"  video        -> /automotive          {base}.mp4")
    return rows


def contact_sheets(manifest):
    """Labelled thumbnail grids so pruning doesn't mean opening 300 files."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default()
    TH, COLS, PAD, LBL, PER = 260, 5, 10, 26, 30
    sheets_dir = os.path.join(OUT, "_contact-sheets")
    os.makedirs(sheets_dir, exist_ok=True)
    by = {}
    for m in manifest:
        if m.get("kind") != "video":
            by.setdefault(m["folder"], []).append(m)
    for folder, rows in by.items():
        rows.sort(key=lambda r: r["file"])
        n_sheets = math.ceil(len(rows) / PER)
        for s in range(n_sheets):
            chunk = rows[s*PER:(s+1)*PER]
            r_n = math.ceil(len(chunk) / COLS)
            sheet = Image.new("RGB", (COLS*(TH+PAD)+PAD,
                                      r_n*(TH+LBL+PAD)+PAD+24), "white")
            d = ImageDraw.Draw(sheet)
            head = f"{folder} -> {chunk[0]['page']}"
            if chunk[0]["section"]:
                head += f"  ({chunk[0]['section']} section)"
            d.text((PAD, 6), f"{head}   sheet {s+1}/{n_sheets}   "
                             f"({len(rows)} images)", fill="black", font=font)
            for i, m in enumerate(chunk):
                im = Image.open(os.path.join(OUT, m["file"]))
                im.thumbnail((TH, TH))
                x = PAD + (i % COLS) * (TH + PAD)
                y = 24 + PAD + (i // COLS) * (TH + LBL + PAD)
                sheet.paste(im, (x + (TH-im.width)//2, y + (TH-im.height)//2))
                d.text((x, y+TH+4), m["source"][:34], fill="black", font=font)
                d.text((x, y+TH+14), m["web_px"], fill="#888888", font=font)
            sheet.save(os.path.join(sheets_dir, f"{folder}-{s+1}.jpg"), quality=80)


# ---------------------------------------------------------------------- upload

def upload(args):
    path = os.path.join(OUT, "manifest.json")
    if not os.path.isfile(path):
        sys.exit("No manifest.json - run 'convert' first.")
    manifest = json.load(open(path, encoding="utf-8"))

    common = xmlrpc.client.ServerProxy(f"{args.url.rstrip('/')}/xmlrpc/2/common")
    uid = common.authenticate(args.db, args.user, args.api_key, {})
    if not uid:
        sys.exit("Authentication failed - check --db, --user and --api-key.")
    models = xmlrpc.client.ServerProxy(f"{args.url.rstrip('/')}/xmlrpc/2/object")
    print(f"Authenticated as uid {uid}\n")

    def put(rel_path, mimetype):
        """Create or update one ir.attachment; return (id, checksum, action)."""
        full = os.path.join(OUT, rel_path)
        name = os.path.basename(rel_path)
        vals = {"name": name,
                "datas": base64.b64encode(open(full, "rb").read()).decode(),
                "mimetype": mimetype,
                "res_model": "ir.ui.view",
                "public": True,
                "website_id": WEBSITE_ID}
        found = models.execute_kw(args.db, uid, args.api_key, "ir.attachment",
                                  "search", [[("name", "=", name),
                                              ("website_id", "=", WEBSITE_ID)]],
                                  {"limit": 1})
        if found:
            models.execute_kw(args.db, uid, args.api_key, "ir.attachment",
                              "write", [found, vals])
            att_id, action = found[0], "updated"
        else:
            att_id = models.execute_kw(args.db, uid, args.api_key,
                                       "ir.attachment", "create", [vals])
            action = "created"
        rec = models.execute_kw(args.db, uid, args.api_key, "ir.attachment",
                                "read", [[att_id]], {"fields": ["checksum"]})[0]
        return att_id, (rec.get("checksum") or "")[:7], action

    live, missing = [], 0
    for m in manifest:
        if not os.path.isfile(os.path.join(OUT, m["file"])):
            missing += 1                      # you deleted it while pruning
            continue
        att_id, csum, action = put(m["file"], m["mimetype"])
        name = os.path.basename(m["file"])
        m["attachment_id"] = att_id
        if m.get("kind") == "video":
            m["url"] = f"/web/content/{att_id}/{name}"
            if m.get("poster_file") and os.path.isfile(os.path.join(OUT, m["poster_file"])):
                pid, pcsum, _ = put(m["poster_file"], "image/webp")
                m["poster_url"] = (f"/web/image/{pid}-{pcsum}/"
                                   f"{os.path.basename(m['poster_file'])}")
        else:
            m["url"] = f"/web/image/{att_id}-{csum}/{name}"
        live.append(m)
        print(f"{action:8s} id={att_id:<7d} {m['url']}")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    write_snippets(live)
    print(f"\n{len(live)} attachments on website {WEBSITE_ID}"
          + (f", {missing} pruned files skipped" if missing else ""))
    print(f"Snippets: ./{OUT}/snippets.html")


def write_snippets(rows):
    by = {}
    for m in rows:
        by.setdefault((m["page"], m["section"]), []).append(m)
    out = []
    for (page, section), items in sorted(by.items()):
        head = page + (f"  ({section} section)" if section else "")
        out.append(f"<!-- ===================== {head} ===================== -->")
        for m in items:
            w, h = m["web_px"].split("x")
            out.append(f"<!-- source: {m['source']} -->")
            if m.get("kind") == "video":
                out.append(
                    f'<video class="img-fluid rounded shadow-sm" width="{w}" height="{h}"\n'
                    f'       poster="{m.get("poster_url","")}"\n'
                    f'       autoplay="autoplay" loop="loop" muted="muted"'
                    f' playsinline="playsinline" preload="metadata"\n'
                    f'       aria-label="{m["alt"]}">\n'
                    f'  <source src="{m["url"]}" type="video/mp4"/>\n</video>')
            else:
                out.append(
                    f'<img src="{m["url"]}"\n     alt="{m["alt"]}"\n'
                    f'     class="img img-fluid rounded shadow-sm o_we_custom_image"\n'
                    f'     loading="lazy" width="{w}" height="{h}"/>')
            out.append("")
    with open(os.path.join(OUT, "snippets.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="read the Drive folder, write WebP + sheets")
    c.add_argument("--media", default=MEDIA, help=f"default: {MEDIA}")
    u = sub.add_parser("upload", help="create the Odoo attachments")
    for flag in ("url", "db", "user", "api-key"):
        u.add_argument(f"--{flag}", required=True)
    args = ap.parse_args()
    if args.cmd == "convert":
        convert(args.media)
    else:
        upload(args)


if __name__ == "__main__":
    main()
