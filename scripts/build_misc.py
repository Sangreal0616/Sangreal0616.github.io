"""Build the web assets for the Miscellaneous gallery (misc.html).

Discovers the full-resolution originals in images/ (named mis*.jpg / mis*.png,
kept out of git) and writes downscaled copies the site actually serves:

    images/misc/<hash>.jpg          up to 1600px, shown in the viewer
    images/misc/thumbs/<hash>.jpg   up to  400px, shown in the grid below it

Filenames are a hash of the encoded image, which matters because GitHub Pages
serves these with Cache-Control: max-age=600. Sequential names like 01.jpg get
reused when the photo set changes, so a returning visitor's browser would keep
showing whatever it cached under that name -- including photos since deleted.
Hashing means changed photos get a new URL and unchanged ones stay cached.

The ordered list of filenames is written into misc.html, so the page never
guesses a URL.

EXIF orientation is applied and then dropped, which both fixes sideways photos
and strips any GPS coordinates before they go on a public site.

To add or remove photos: change what's in images/, then rerun

    python scripts/build_misc.py

Nothing else needs editing -- the file list is discovered, the manifest in
misc.html is rewritten, and assets no longer referenced are deleted.

Requires Pillow:  pip install Pillow
"""
import glob
import hashlib
import io
import json
import os
import re

from PIL import Image, ImageOps

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "images")
OUT = os.path.join(SRC, "misc")
THUMBS = os.path.join(OUT, "thumbs")
PAGE = os.path.join(REPO, "misc.html")

VIEW_MAX = 1600
THUMB_MAX = 400
VIEW_QUALITY = 85
THUMB_QUALITY = 78

MANIFEST_RE = re.compile(
    r'(<script id="misc-photos" type="application/json">)(.*?)(</script>)', re.S)


def sort_key(path):
    """mis2 < mis4 < mis10 < 'mis10 (2)' -- numeric, with variants after their base."""
    name = os.path.basename(path)
    m = re.match(r"mis(\d+)(?:\s*\((\d+)\))?", name, re.I)
    if not m:
        return (10**6, 0, name.lower())
    return (int(m.group(1)), int(m.group(2) or 1), name.lower())


def discover():
    found = []
    for ext in ("jpg", "jpeg", "png"):
        found += glob.glob(os.path.join(SRC, f"mis*.{ext}"))
        found += glob.glob(os.path.join(SRC, f"mis*.{ext.upper()}"))
    # images/misc/ lives under images/, so make sure we never pick our own output
    found = [f for f in found if os.path.dirname(f) == SRC]
    return sorted(set(found), key=sort_key)


def encode(im, box, quality):
    """Return (filename, bytes) for a downscaled copy, named by content hash."""
    copy = im.copy()
    copy.thumbnail((box, box), Image.LANCZOS)
    buf = io.BytesIO()
    copy.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    data = buf.getvalue()
    return hashlib.sha1(data).hexdigest()[:12] + ".jpg", data


def main():
    sources = discover()
    if not sources:
        raise SystemExit(f"no mis* images found in {SRC}")

    os.makedirs(THUMBS, exist_ok=True)
    total_src = total_out = 0
    manifest = []

    for src in sources:
        total_src += os.path.getsize(src)
        im = ImageOps.exif_transpose(Image.open(src))
        if im.mode != "RGB":
            im = im.convert("RGB")

        pair = []
        for box, quality, folder in ((VIEW_MAX, VIEW_QUALITY, OUT),
                                     (THUMB_MAX, THUMB_QUALITY, THUMBS)):
            name, data = encode(im, box, quality)
            with open(os.path.join(folder, name), "wb") as fh:
                fh.write(data)
            total_out += len(data)
            pair.append(name)

        manifest.append(pair)
        print(f"{pair[0]}  <- {os.path.basename(src)}")

    # delete anything the manifest no longer points at
    wanted = {OUT: {p[0] for p in manifest}, THUMBS: {p[1] for p in manifest}}
    for folder, keep in wanted.items():
        for path in glob.glob(os.path.join(folder, "*.jpg")):
            if os.path.basename(path) not in keep:
                os.remove(path)
                print(f"removed unreferenced {os.path.relpath(path, REPO)}")

    # write the ordered filename list into the page
    html = io.open(PAGE, encoding="utf-8").read()
    if not MANIFEST_RE.search(html):
        raise SystemExit('could not find <script id="misc-photos"> in misc.html')
    body = "\n" + ",\n".join("  " + json.dumps(p) for p in manifest) + "\n"
    patched = MANIFEST_RE.sub(
        lambda m: m.group(1) + "[" + body + "]" + m.group(3), html, count=1)
    if patched != html:
        io.open(PAGE, "w", encoding="utf-8", newline="\n").write(patched)
        print(f"\nrewrote manifest in misc.html ({len(manifest)} photos)")
    else:
        print(f"\nmanifest already current ({len(manifest)} photos)")

    mb = 1024 * 1024
    print(f"{len(sources)} photos: {total_src / mb:.1f} MB originals "
          f"-> {total_out / mb:.1f} MB served")


if __name__ == "__main__":
    main()
