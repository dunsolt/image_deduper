from pathlib import Path
from PIL import Image
import hashlib
import csv
from collections import defaultdict

ROOT = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")

OUTPUT_DIR = Path.home() / "tools/image_deduper/_dedupe_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GROUPS_CSV = OUTPUT_DIR / "character_engine_duplicate_groups.csv"
FILES_CSV = OUTPUT_DIR / "character_engine_duplicate_files.csv"
ERRORS_CSV = OUTPUT_DIR / "character_engine_duplicate_errors.csv"

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}


def image_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def pixel_hash(path: Path):
    """
    Hash decoded pixel data so metadata/filename differences don't matter.
    """
    with Image.open(path) as img:
        img = img.convert("RGBA")

        hasher = hashlib.sha256()
        hasher.update(str(img.size).encode())
        hasher.update(img.tobytes())

        return hasher.hexdigest(), img.size


print("Scanning Character Engine for duplicate images...\n")

hash_to_files = defaultdict(list)
errors = []
count = 0

for path in image_files(ROOT):
    try:
        digest, dimensions = pixel_hash(path)
        hash_to_files[digest].append({
            "path": path,
            "width": dimensions[0],
            "height": dimensions[1],
        })

        count += 1

        if count % 250 == 0:
            print(f"Indexed {count:,} images...")

    except Exception as e:
        errors.append((str(path), str(e)))

duplicate_groups = []
duplicate_files = []

group_id = 0
duplicate_image_count = 0
duplicate_copy_count = 0

for digest, files in hash_to_files.items():
    if len(files) > 1:
        group_id += 1
        copies = len(files)
        duplicate_image_count += 1
        duplicate_copy_count += copies

        sample_path = str(files[0]["path"])

        duplicate_groups.append({
            "group_id": group_id,
            "pixel_hash": digest,
            "copies": copies,
            "width": files[0]["width"],
            "height": files[0]["height"],
            "sample_file": sample_path,
        })

        for item in files:
            relative_folder = item["path"].parent.relative_to(ROOT)
            duplicate_files.append({
                "group_id": group_id,
                "pixel_hash": digest,
                "file_path": str(item["path"]),
                "relative_folder": str(relative_folder),
                "filename": item["path"].name,
                "width": item["width"],
                "height": item["height"],
            })

with open(GROUPS_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_id",
            "pixel_hash",
            "copies",
            "width",
            "height",
            "sample_file",
        ],
    )
    writer.writeheader()
    writer.writerows(duplicate_groups)

with open(FILES_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_id",
            "pixel_hash",
            "file_path",
            "relative_folder",
            "filename",
            "width",
            "height",
        ],
    )
    writer.writeheader()
    writer.writerows(duplicate_files)

with open(ERRORS_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "error"])
    writer.writerows(errors)

print("\nDONE")
print(f"Images scanned: {count:,}")
print(f"Duplicate groups: {group_id:,}")
print(f"Files involved in duplicate groups: {duplicate_copy_count:,}")
print(f"Truly duplicated extra copies: {duplicate_copy_count - group_id:,}")
print(f"Errors: {len(errors):,}")

print(f"\nReports:")
print(GROUPS_CSV)
print(FILES_CSV)
print(ERRORS_CSV)