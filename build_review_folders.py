from pathlib import Path
import csv
import shutil

PROJECT_ROOT = Path.home() / "tools/image_deduper"
CSV_FILE = PROJECT_ROOT / "_dedupe_results/folder_suggestions_centroid.csv"
DESTINATION = Path("/mnt/c/Users/Danvx/Desktop/GPT Images - REVIEW")

DESTINATION.mkdir(parents=True, exist_ok=True)


def safe_copy(source: Path, destination: Path):
    """
    Copy without overwriting an existing file.
    """
    destination.mkdir(parents=True, exist_ok=True)

    target = destination / source.name

    if not target.exists():
        shutil.copy2(source, target)
        return target

    stem = source.stem
    suffix = source.suffix
    counter = 2

    while True:
        candidate = destination / f"{stem}_{counter}{suffix}"

        if not candidate.exists():
            shutil.copy2(source, candidate)
            return candidate

        counter += 1


copied = 0
missing = 0

with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        source = Path(row["new_file"])

        if not source.exists():
            print(f"Missing: {source}")
            missing += 1
            continue

        status = row["status"]
        suggested_folder = row["suggested_folder"]

        if status == "Confident":
            target_folder = (
                DESTINATION
                / "Confident"
                / Path(suggested_folder)
            )

        elif status == "Needs Review":
            # Keep the best guess visible,
            # but separate it from confident classifications.
            target_folder = (
                DESTINATION
                / "Needs Review"
                / Path(suggested_folder)
            )

        else:
            target_folder = DESTINATION / "Unknown"

        safe_copy(source, target_folder)

        copied += 1

        if copied % 250 == 0:
            print(f"Copied {copied:,} images...")


print("\nDONE")
print(f"Copied: {copied:,}")
print(f"Missing: {missing:,}")
print(f"\nReview tree:\n{DESTINATION}")