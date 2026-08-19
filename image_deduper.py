from pathlib import Path
from PIL import Image
import hashlib
import csv

ORGANISED = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")
NEW_DUMP = Path("/mnt/c/Users/Danvx/Desktop/icloud_dump")
OUTPUT = Path("/home/dan/tools/image_deduper/_dedupe_results")
OUTPUT.mkdir(exist_ok=True)

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}


def image_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def pixel_hash(path: Path):
    """
    Decode the image and hash the actual pixel data.

    Metadata, filename and PNG/JPEG encoding do not affect this hash.
    """
    with Image.open(path) as img:
        img = img.convert("RGBA")

        hasher = hashlib.sha256()

        # Include dimensions so differently shaped images cannot match.
        hasher.update(str(img.size).encode())
        hasher.update(img.tobytes())

        return hasher.hexdigest(), img.size


print("Indexing organised archive...")

organised_hashes = {}
organised_count = 0
errors = []

for path in image_files(ORGANISED):
    try:
        digest, dimensions = pixel_hash(path)

        organised_hashes.setdefault(digest, []).append({
            "path": path,
            "dimensions": dimensions,
        })

        organised_count += 1

        if organised_count % 250 == 0:
            print(f"  Indexed {organised_count:,} organised images...")

    except Exception as e:
        errors.append((str(path), str(e)))


print(f"\nIndexed {organised_count:,} organised images.")
print("\nComparing new dump...")

matches = []
new_images = []
new_count = 0

for path in image_files(NEW_DUMP):

    # Ignore our own output directory
    if OUTPUT in path.parents:
        continue

    try:
        digest, dimensions = pixel_hash(path)
        new_count += 1

        if digest in organised_hashes:
            for existing in organised_hashes[digest]:
                matches.append({
                    "new_file": str(path),
                    "existing_file": str(existing["path"]),
                    "pixel_hash": digest,
                    "width": dimensions[0],
                    "height": dimensions[1],
                })
        else:
            new_images.append({
                "new_file": str(path),
                "pixel_hash": digest,
                "width": dimensions[0],
                "height": dimensions[1],
            })

        if new_count % 250 == 0:
            print(
                f"  Checked {new_count:,} new images "
                f"| duplicates: {len(matches):,} "
                f"| new: {len(new_images):,}"
            )

    except Exception as e:
        errors.append((str(path), str(e)))


with open(OUTPUT / "exact_pixel_matches.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "new_file",
            "existing_file",
            "pixel_hash",
            "width",
            "height",
        ],
    )
    writer.writeheader()
    writer.writerows(matches)


with open(OUTPUT / "new_images.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "new_file",
            "pixel_hash",
            "width",
            "height",
        ],
    )
    writer.writeheader()
    writer.writerows(new_images)


with open(OUTPUT / "errors.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "error"])
    writer.writerows(errors)


print("\nDONE")
print(f"Organised archive: {organised_count:,} images")
print(f"New dump checked: {new_count:,} images")
print(f"Pixel-identical matches: {len(matches):,}")
print(f"Genuinely unmatched: {len(new_images):,}")
print(f"Errors: {len(errors):,}")
print(f"\nReports saved to:\n{OUTPUT}")