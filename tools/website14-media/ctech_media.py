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
import argparse, base64, hashlib, json, math, os, re, sys, time, xmlrpc.client

VERSION = 5                 # bumped whenever this file changes
MEDIA = r"G:\My Drive\C-Tech\Marketing\Websters\Media"
OUT = "website14-media"
WEBSITE_ID = 14
MAXW, QUALITY = 1600, 82
FORMAT = "webp"             # overridden by 'convert --format jpeg'
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

def convert(media_root, fmt=None):
    from PIL import Image, ImageOps
    fmt = (fmt or FORMAT).lower()
    ext = ".jpg" if fmt in ("jpg", "jpeg") else f".{fmt}"
    pil_fmt = "JPEG" if fmt in ("jpg", "jpeg") else fmt.upper()
    mime = "image/jpeg" if fmt in ("jpg", "jpeg") else f"image/{fmt}"

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
            out = os.path.join(dst_dir, f"{folder}-{slug(name)}{ext}")
            save_kw = {"quality": QUALITY}
            if pil_fmt == "WEBP":
                save_kw["method"] = 6
            im.save(out, pil_fmt, **save_kw)
            manifest.append(dict(source=name, folder=folder,
                                 file=os.path.relpath(out, OUT).replace("\\", "/"),
                                 page=page, section=section,
                                 alt=os.path.splitext(name)[0],
                                 web_px=f"{im.size[0]}x{im.size[1]}",
                                 web_kb=round(os.path.getsize(out) / 1024, 1),
                                 mimetype=mime))
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
    print(f"Authenticated as uid {uid}")

    def rpc(model, method, *a, **kw):
        """One RPC, retried with backoff when Odoo rate-limits us."""
        for attempt in range(6):
            try:
                return models.execute_kw(args.db, uid, args.api_key,
                                         model, method, list(a), kw)
            except xmlrpc.client.ProtocolError as e:
                if e.errcode != 429 or attempt == 5:
                    raise
                wait = min(60, 5 * 2 ** attempt)
                print(f"  rate-limited, waiting {wait}s ...")
                time.sleep(wait)

    # One call instead of a search per file: what is already on website 14.
    existing = {r["name"]: r["id"] for r in
                rpc("ir.attachment", "search_read",
                    [("website_id", "=", WEBSITE_ID)], fields=["name"])}
    print(f"{len(existing)} attachments already on website {WEBSITE_ID}\n")

    def put(rel_path, mimetype):
        """Create/update one attachment. Returns (id, action)."""
        name = os.path.basename(rel_path)
        if name in existing and not args.force:
            return existing[name], "skipped"
        vals = {"name": name,
                "datas": base64.b64encode(
                    open(os.path.join(OUT, rel_path), "rb").read()).decode(),
                "mimetype": mimetype,
                "res_model": "ir.ui.view",
                "public": True,
                "website_id": WEBSITE_ID}
        if name in existing:
            rpc("ir.attachment", "write", [existing[name]], vals)
            return existing[name], "updated"
        att_id = rpc("ir.attachment", "create", vals)
        existing[name] = att_id
        return att_id, "created"

    def verify(att_id):
        """Odoo only sets checksum once real bytes are stored."""
        r = rpc("ir.attachment", "read", [att_id],
                fields=["checksum", "file_size"])[0]
        return bool(r.get("checksum")) and bool(r.get("file_size"))

    def save():
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

    checked = False
    live, missing, done = [], 0, 0
    total = sum(1 for m in manifest
                if os.path.isfile(os.path.join(OUT, m["file"])))
    for m in manifest:
        if not os.path.isfile(os.path.join(OUT, m["file"])):
            missing += 1                      # deleted while pruning
            continue
        att_id, action = put(m["file"], m["mimetype"])
        name = os.path.basename(m["file"])
        m["attachment_id"] = att_id
        if m.get("kind") == "video":
            m["url"] = f"/web/content/{att_id}/{name}"
            poster = m.get("poster_file")
            if poster and os.path.isfile(os.path.join(OUT, poster)):
                pid, _ = put(poster, "image/webp")
                m["poster_url"] = f"/web/image/{pid}/{os.path.basename(poster)}"
        else:
            m["url"] = f"/web/image/{att_id}/{name}"
        if not checked and action in ("created", "updated"):
            checked = True
            if not verify(att_id):
                sys.exit(
                    f"\nERROR: attachment {att_id} stored no file data "
                    f"(checksum empty).\n"
                    f"Odoo accepted the record but dropped the binary, so every "
                    f"image would be a placeholder\nand the website editor's "
                    f"media dialog will crash on it.\n"
                    f"Stopping after one file rather than creating hundreds of "
                    f"broken records.\n"
                    f"Run 'check' for details, and 'prune --all --yes' to clear "
                    f"anything already uploaded.")
        live.append(m)
        done += 1
        print(f"[{done:3d}/{total}] {action:8s} id={att_id:<7d} {m['url']}")
        if done % 10 == 0:
            save()                            # so a crash never loses progress
        if action != "skipped" and args.delay:
            time.sleep(args.delay)

    save()
    write_snippets(live)
    print(f"\n{len(live)} attachments on website {WEBSITE_ID}"
          + (f", {missing} pruned files skipped" if missing else ""))
    print(f"Snippets: ./{OUT}/snippets.html")


def connect(args):
    common = xmlrpc.client.ServerProxy(f"{args.url.rstrip('/')}/xmlrpc/2/common")
    uid = common.authenticate(args.db, args.user, args.api_key, {})
    if not uid:
        sys.exit("Authentication failed - check --db, --user and --api-key.")
    models = xmlrpc.client.ServerProxy(f"{args.url.rstrip('/')}/xmlrpc/2/object")

    def rpc(model, method, *a, **kw):
        for attempt in range(6):
            try:
                return models.execute_kw(args.db, uid, args.api_key,
                                         model, method, list(a), kw)
            except xmlrpc.client.ProtocolError as e:
                if e.errcode != 429 or attempt == 5:
                    raise
                wait = min(60, 5 * 2 ** attempt)
                print(f"  rate-limited, waiting {wait}s ...")
                time.sleep(wait)
    print(f"Authenticated as uid {uid}")
    return rpc


def fetch_website_attachments(rpc):
    rows = rpc("ir.attachment", "search_read",
               [("website_id", "=", WEBSITE_ID)],
               fields=["name", "file_size", "mimetype"], order="name")
    return rows


def local_names():
    """Every filename currently sitting in ./website14-media/."""
    names = set()
    for root, _dirs, files in os.walk(OUT):
        if os.path.basename(root) == "_contact-sheets":
            continue
        for f in files:
            if not f.endswith((".json", ".html")):
                names.add(f)
    return names


def our_prefixes():
    return tuple(f"{folder}-" for folder, _p, _s in FOLDERS.values()) \
           + ("closure-testing-",)


def cmd_list(args):
    rows = fetch_website_attachments(connect(args))
    ours = local_names()
    pref = our_prefixes()
    print(f"\n{len(rows)} attachments on website {WEBSITE_ID}\n")
    print(f"{'id':<8} {'size':>9}  {'':<3} name")
    groups, orphans = {}, 0
    for r in rows:
        prefix = r["name"].split("-")[0]
        groups[prefix] = groups.get(prefix, 0) + 1
        stale = r["name"].startswith(pref) and r["name"] not in ours
        mark = "  *" if stale else "   "
        orphans += stale
        print(f"{r['id']:<8} {r['file_size']/1024:8.1f}K {mark} {r['name']}")
    print(f"\nby name prefix:")
    for k, v in sorted(groups.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<16} {v:4d}")
    total = sum(r["file_size"] for r in rows)
    print(f"\ntotal {total/1048576:.1f} MB")
    if orphans:
        print(f"{orphans} marked * are ours but no longer in ./{OUT}/ - "
              f"'prune' would delete them")
    else:
        print(f"nothing stale - 'prune' would delete nothing")


def cmd_prune(args):
    """Delete attachments on the website that you removed locally."""
    rpc = connect(args)
    rows = fetch_website_attachments(rpc)
    ours = local_names()
    doomed = [r for r in rows
              if r["name"].startswith(our_prefixes())
              and (args.all or r["name"] not in ours)]
    if not doomed:
        print(f"\nNothing to prune - every {WEBSITE_ID} attachment with one of "
              f"our prefixes is still in ./{OUT}/.")
        return
    size = sum(r["file_size"] for r in doomed)
    print(f"\n{len(doomed)} attachments on website {WEBSITE_ID} are no longer "
          f"in ./{OUT}/ ({size/1048576:.1f} MB):\n")
    for r in doomed:
        print(f"  {r['id']:<8} {r['name']}")
    if not args.yes:
        print(f"\nDry run. Re-run with --yes to delete these {len(doomed)}.")
        return
    print()
    for i in range(0, len(doomed), 50):           # batch, stays under the limiter
        batch = [r["id"] for r in doomed[i:i+50]]
        rpc("ir.attachment", "unlink", batch)
        print(f"  deleted {i+len(batch)}/{len(doomed)}")
        time.sleep(args.delay)
    print(f"\nDeleted {len(doomed)} attachments.")
    print("Any <img> already pasted into a page view that pointed at one of "
          "these is now broken - check snippets.html.")


def cmd_check(args):
    """Read one attachment back and report why /web/image might not serve it."""
    common = xmlrpc.client.ServerProxy(f"{args.url.rstrip('/')}/xmlrpc/2/common")
    ver = common.version()
    rpc = connect(args)
    print(f"Odoo {ver.get('server_serie')} "
          f"(protocol {ver.get('protocol_version')})\n")

    dom = [("id", "=", int(args.id))] if args.id else \
          [("website_id", "=", WEBSITE_ID), ("name", "like", "closure-%")]
    rows = rpc("ir.attachment", "search_read", dom,
               fields=["name", "type", "mimetype", "file_size", "checksum",
                       "res_model", "res_id", "res_field", "public", "url",
                       "website_id", "store_fname"],
               limit=1, order="id")
    if not rows:
        sys.exit("No matching attachment found.")
    r = rows[0]
    for k in ("id", "name", "type", "mimetype", "file_size", "checksum",
              "res_model", "res_id", "res_field", "public", "url",
              "website_id", "store_fname"):
        print(f"  {k:<12} {r.get(k)!r}")

    # does the binary actually round-trip?
    got = rpc("ir.attachment", "read", [r["id"]], fields=["datas"])[0]["datas"]
    n = len(base64.b64decode(got)) if got else 0
    print(f"\n  datas        {n} bytes read back")
    if n:
        head = base64.b64decode(got)[:16]
        is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        print(f"  magic        {head[:12]!r}  -> "
              f"{'valid WebP' if is_webp else 'NOT a WebP'}")

    print(f"\n  /web/content/{r['id']}/{r['name']}   <- raw bytes, no processing")
    print(f"  /web/image/{r['id']}/{r['name']}     <- image pipeline")
    if r["file_size"] and n:
        print("\nBinary is present and intact. If /web/image shows the "
              "placeholder but /web/content downloads fine, this Odoo's image "
              "pipeline is not serving WebP - re-run 'convert' with "
              "--format jpeg and 'upload --force'.")
    else:
        print("\nThe binary did not store. That is the problem, not WebP.")


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
    c.add_argument("--format", default=FORMAT, choices=["webp", "jpeg", "jpg"],
                   help="output image format (default webp)")
    u = sub.add_parser("upload", help="create the Odoo attachments")
    for flag in ("url", "db", "user", "api-key"):
        u.add_argument(f"--{flag}", required=True)
    u.add_argument("--delay", type=float, default=0.4,
                   help="seconds between writes, eases Odoo's rate limit "
                        "(default 0.4)")
    u.add_argument("--force", action="store_true",
                   help="re-upload files that are already on website 14")

    l = sub.add_parser("list", help=f"show every attachment on website {WEBSITE_ID}")
    p = sub.add_parser("prune", help="delete attachments you removed locally")
    for parser in (l, p):
        for flag in ("url", "db", "user", "api-key"):
            parser.add_argument(f"--{flag}", required=True)
    p.add_argument("--yes", action="store_true", help="actually delete")
    p.add_argument("--all", action="store_true",
                   help="delete ALL of ours on the website, not just the "
                        "ones missing locally")
    p.add_argument("--delay", type=float, default=0.4)

    ck = sub.add_parser("check", help="diagnose one attachment end to end")
    for flag in ("url", "db", "user", "api-key"):
        ck.add_argument(f"--{flag}", required=True)
    ck.add_argument("--id", help="attachment id (default: first closure- one)")
    args = ap.parse_args()
    print(f"ctech_media.py v{VERSION}  ({os.path.abspath(__file__)})\n")
    if args.cmd == "convert":
        convert(args.media, args.format)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "prune":
        cmd_prune(args)
    elif args.cmd == "check":
        cmd_check(args)
    else:
        upload(args)


if __name__ == "__main__":
    main()
