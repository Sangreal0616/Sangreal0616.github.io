"""Build the web assets for the Miscellaneous gallery.

Reads the full-resolution originals in images/ (named mis*.jpg / mis*.png, kept
out of git) and writes downscaled copies the site actually serves:

    images/misc/NN.jpg          up to 1600px, shown in the viewer
    images/misc/thumbs/NN.jpg   up to  400px, shown in the grid below it

EXIF orientation is applied and then dropped, which both fixes sideways photos
and strips any GPS coordinates before they go on a public site.

Adding photos: drop them in images/, add the filenames to ORDER, rerun

    python scripts/build_misc.py

then bump COUNT in the gallery script at the bottom of index.html.

Requires Pillow:  pip install Pillow
"""
import os
from PIL import Image, ImageOps

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "images")
OUT = os.path.join(SRC, "misc")
THUMBS = os.path.join(OUT, "thumbs")

# Source files, in the order they become 01.jpg, 02.jpg, ... The " (2)" names
# are distinct photos, not duplicates -- all 16 hash differently.
ORDER = [
    "mis1.jpg",
    "mis2.jpg",
    "mis3.jpg",
    "mis4.jpg",
    "mis5 (2).jpg",
    "mis6 (2).jpg",
    "mis7.png",
    "mis8.jpg",
    "mis9.jpg",
    "mis10.jpg",
    "mis10 (2).jpg",
    "mis11 (2).jpg",
    "mis12.jpg",
    "mis12 (2).jpg",
    "mis13.jpg",
    "mis14.jpg",
]

VIEW_MAX = 1600
THUMB_MAX = 400


def main():
    os.makedirs(THUMBS, exist_ok=True)
    total_src = total_out = 0

    for i, name in enumerate(ORDER, start=1):
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            raise SystemExit(f"missing source image: {src}")
        total_src += os.path.getsize(src)

        im = ImageOps.exif_transpose(Image.open(src))
        if im.mode != "RGB":
            im = im.convert("RGB")

        out_name = f"{i:02d}.jpg"
        for box, quality, folder in ((VIEW_MAX, 85, OUT), (THUMB_MAX, 78, THUMBS)):
            copy = im.copy()
            copy.thumbnail((box, box), Image.LANCZOS)
            path = os.path.join(folder, out_name)
            copy.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
            total_out += os.path.getsize(path)

        print(f"{out_name}  <- {name}")

    mb = 1024 * 1024
    print(f"\n{len(ORDER)} photos: {total_src / mb:.1f} MB originals "
          f"-> {total_out / mb:.1f} MB served")


if __name__ == "__main__":
    main()
