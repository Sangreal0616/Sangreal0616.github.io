"""Build the web assets for the Miscellaneous gallery (misc.html).

Discovers the full-resolution originals in images/ (named mis*.jpg / mis*.png,
kept out of git) and writes downscaled copies the site actually serves:

    images/misc/NN.jpg          up to 1600px, shown in the viewer
    images/misc/thumbs/NN.jpg   up to  400px, shown in the grid below it

EXIF orientation is applied and then dropped, which both fixes sideways photos
and strips any GPS coordinates before they go on a public site.

To add or remove photos: change what's in images/, then rerun

    python scripts/build_misc.py

Nothing else needs editing -- the file list is discovered, stale outputs from a
previous larger set are deleted, and the data-count on misc.html is rewritten
to match.

Requires Pillow:  pip install Pillow
"""
import os
import re
import io
import glob

from PIL import Image, ImageOps

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "images")
OUT = os.path.join(SRC, "misc")
THUMBS = os.path.join(OUT, "thumbs")
PAGE = os.path.join(REPO, "misc.html")

VIEW_MAX = 1600
THUMB_MAX = 400


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


def main():
    sources = discover()
    if not sources:
        raise SystemExit(f"no mis* images found in {SRC}")

    os.makedirs(THUMBS, exist_ok=True)
    total_src = total_out = 0
    keep = set()

    for i, src in enumerate(sources, start=1):
        total_src += os.path.getsize(src)
        im = ImageOps.exif_transpose(Image.open(src))
        if im.mode != "RGB":
            im = im.convert("RGB")

        out_name = f"{i:02d}.jpg"
        keep.add(out_name)
        for box, quality, folder in ((VIEW_MAX, 85, OUT), (THUMB_MAX, 78, THUMBS)):
            copy = im.copy()
            copy.thumbnail((box, box), Image.LANCZOS)
            path = os.path.join(folder, out_name)
            copy.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
            total_out += os.path.getsize(path)

        print(f"{out_name}  <- {os.path.basename(src)}")

    # drop leftovers from a previous, larger run
    for folder in (OUT, THUMBS):
        for stale in glob.glob(os.path.join(folder, "*.jpg")):
            if os.path.basename(stale) not in keep:
                os.remove(stale)
                print(f"removed stale {os.path.relpath(stale, REPO)}")

    # keep the page's photo count in sync
    html = io.open(PAGE, encoding="utf-8").read()
    patched, n = re.subn(r'(id="gallery"[^>]*\bdata-count=")\d+(")',
                         lambda m: f"{m.group(1)}{len(sources)}{m.group(2)}", html)
    if n == 1:
        if patched != html:
            io.open(PAGE, "w", encoding="utf-8", newline="\n").write(patched)
            print(f"updated data-count in misc.html -> {len(sources)}")
    else:
        print(f"WARNING: could not find data-count in misc.html "
              f"(matched {n} times) -- set it to {len(sources)} by hand")

    mb = 1024 * 1024
    print(f"\n{len(sources)} photos: {total_src / mb:.1f} MB originals "
          f"-> {total_out / mb:.1f} MB served")


if __name__ == "__main__":
    main()
