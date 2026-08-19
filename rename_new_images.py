from pathlib import Path
import csv

FOLDER = Path(r"C:\Users\Danvx\Desktop\GPT Images - NEW ONLY")

REPORT = Path(
    r"C:\Users\Danvx\Desktop\image_deduper\_dedupe_results\rename_manifest.csv"
)

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}


images = sorted(
    [
        path
        for path in FOLDER.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ],
    key=lambda p: p.name.lower()
)


print(f"Found {len(images):,} images.")
print("Renaming...")


rows = []

for index, old_path in enumerate(images, start=1):

    new_name = f"gen_{index:06d}{old_path.suffix.lower()}"
    new_path = FOLDER / new_name

    # Very unlikely, but prevents accidental overwrites.
    if new_path.exists() and new_path != old_path:
        raise FileExistsError(
            f"Target already exists:\n{new_path}"
        )

    rows.append({
        "index": index,
        "old_filename": old_path.name,
        "new_filename": new_name,
        "old_path": str(old_path),
        "new_path": str(new_path),
    })


# Two-stage rename prevents collisions with existing filenames.
temporary_paths = []

for index, (old_path, row) in enumerate(zip(images, rows), start=1):
    temp_path = FOLDER / f"__rename_temp_{index:06d}{old_path.suffix.lower()}"

    old_path.rename(temp_path)

    temporary_paths.append(
        (temp_path, FOLDER / row["new_filename"])
    )


for temp_path, final_path in temporary_paths:
    temp_path.rename(final_path)


REPORT.parent.mkdir(parents=True, exist_ok=True)

with open(REPORT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "index",
            "old_filename",
            "new_filename",
            "old_path",
            "new_path",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


print("\nDONE")
print(f"Renamed: {len(images):,}")
print(f"Manifest:\n{REPORT}")