from pathlib import Path
import csv
import re
import shutil


GEN_PATTERN = re.compile(r"^gen_(\d{6})$", re.IGNORECASE)

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

CHARACTER_ENGINE = Path("/mnt/c/Users/Danvx/Character Engine")
INBOX = CHARACTER_ENGINE / "ZZ_Inbox"
SOURCE = INBOX / "new_only"
DESTINATION = INBOX / "ready_to_sort"
REPORTS = INBOX / "reports"
REPORT = REPORTS / "rename_manifest.csv"


def image_files(root: Path):
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )


def find_highest_index(root: Path, *, exclude: Path | None = None):
    highest = 0

    for path in root.rglob("*"):
        if exclude is not None:
            try:
                path.relative_to(exclude)
                continue
            except ValueError:
                pass

        if not path.is_file():
            continue

        match = GEN_PATTERN.match(path.stem)

        if match:
            highest = max(highest, int(match.group(1)))

    return highest


def main():
    print("\n=== Image Renamer ===\n")

    if not CHARACTER_ENGINE.exists() or not CHARACTER_ENGINE.is_dir():
        print(f"Error: Character Engine folder is invalid:\n{CHARACTER_ENGINE}")
        return

    if not SOURCE.exists() or not SOURCE.is_dir():
        print(
            "Error: new_only folder does not exist.\n"
            "Run image_deduper.py first.\n\n"
            f"Expected:\n{SOURCE}"
        )
        return

    DESTINATION.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    source_images = image_files(SOURCE)
    existing_output = image_files(DESTINATION)

    if not source_images:
        print(f"Nothing to rename. new_only is empty:\n{SOURCE}")
        return

    if existing_output:
        print(
            "Safety stop: ready_to_sort already contains images.\n"
            "Sort or clear that folder before starting another rename batch.\n\n"
            f"Folder:\n{DESTINATION}"
        )
        return

    # Only archived files outside ZZ_Inbox determine the next permanent ID.
    highest_existing = find_highest_index(
        CHARACTER_ENGINE,
        exclude=INBOX,
    )
    start_index = highest_existing + 1

    print(f"Source:              {SOURCE}")
    print(f"Destination:         {DESTINATION}")
    print(f"Images to copy:      {len(source_images):,}")
    print(f"Highest archive ID:  gen_{highest_existing:06d}")
    print(f"Starting ID:         gen_{start_index:06d}")

    confirmation = input("\nCreate renamed copies? [Y/n]: ").strip().lower()

    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    rows = []
    copied = 0
    errors = []

    for index, source_path in enumerate(source_images, start=start_index):
        new_name = f"gen_{index:06d}{source_path.suffix.lower()}"
        destination_path = DESTINATION / new_name

        try:
            if destination_path.exists():
                raise FileExistsError(
                    f"Target already exists: {destination_path}"
                )

            shutil.copy2(source_path, destination_path)

            rows.append({
                "index": index,
                "source_filename": source_path.name,
                "new_filename": new_name,
                "source_path": str(source_path),
                "destination_path": str(destination_path),
            })
            copied += 1

        except Exception as e:
            errors.append((str(source_path), str(e)))
            print(f"ERROR: {source_path}")
            print(e)

    with open(
        REPORT,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "source_filename",
                "new_filename",
                "source_path",
                "destination_path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    error_report = REPORTS / "rename_errors.csv"

    with open(
        error_report,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nDONE")
    print(f"Renamed copies created: {copied:,}")
    print(f"Errors:                 {len(errors):,}")
    print(f"\nReady to sort:\n{DESTINATION}")
    print(f"\nManifest:\n{REPORT}")


if __name__ == "__main__":
    main()
