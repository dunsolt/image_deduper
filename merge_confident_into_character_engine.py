from pathlib import Path
import csv
import shutil

PROJECT_ROOT = Path.home() / "tools/image_deduper"
SOURCE = Path("/mnt/c/Users/Danvx/Desktop/GPT-REVIEW/Confident")
DESTINATION = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")
MANIFEST = PROJECT_ROOT / "_dedupe_results/final_merge_manifest.csv"

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}


def unique_destination(target: Path) -> Path:
    """
    Never overwrite an existing file.
    If the filename already exists, add _2, _3, etc.
    """
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 2

    while True:
        candidate = target.parent / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            return candidate

        counter += 1


if not SOURCE.exists():
    raise FileNotFoundError(f"Source folder not found:\n{SOURCE}")

DESTINATION.mkdir(parents=True, exist_ok=True)
MANIFEST.parent.mkdir(parents=True, exist_ok=True)

images = [
    path
    for path in SOURCE.rglob("*")
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
]

print(f"Found {len(images):,} verified images.")
print("Merging into Character Engine...\n")

rows = []
copied = 0
errors = 0

for source_file in images:
    try:
        # Preserve the folder structure beneath Confident.
        relative_path = source_file.relative_to(SOURCE)

        target = DESTINATION / relative_path

        target.parent.mkdir(parents=True, exist_ok=True)

        final_target = unique_destination(target)

        shutil.copy2(source_file, final_target)

        rows.append({
            "source_file": str(source_file),
            "destination_file": str(final_target),
            "relative_folder": str(relative_path.parent),
        })

        copied += 1

        if copied % 250 == 0:
            print(f"Copied {copied:,} images...")

    except Exception as e:
        print(f"ERROR: {source_file}")
        print(e)
        errors += 1


with open(
    MANIFEST,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "source_file",
            "destination_file",
            "relative_folder",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


print("\nDONE")
print(f"Copied: {copied:,}")
print(f"Errors: {errors:,}")
print(f"\nManifest:\n{MANIFEST}")
print(f"\nCharacter Engine:\n{DESTINATION}")