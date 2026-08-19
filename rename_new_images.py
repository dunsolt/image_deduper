from pathlib import Path
import csv
import re

GEN_PATTERN = re.compile(r"^gen_(\d{6})$", re.IGNORECASE)

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

DEFAULT_NAME_SOURCE = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")


def ask_path(prompt, default=None):
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        path = Path(value) if value else default
    else:
        value = input(f"{prompt}: ").strip()
        path = Path(value)

    return path.expanduser()


def find_highest_index(root: Path):
    highest = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        match = GEN_PATTERN.match(path.stem)

        if match:
            highest = max(highest, int(match.group(1)))

    return highest


def main():
    print("\n=== Image Renamer ===\n")

    folder = ask_path("Folder to rename")

    name_source = ask_path(
        "Existing archive to check for used gen numbers",
        DEFAULT_NAME_SOURCE,
    )

    if not folder.exists() or not folder.is_dir():
        print(f"\nError: rename folder is invalid:\n{folder}")
        return

    if not name_source.exists() or not name_source.is_dir():
        print(f"\nError: archive folder is invalid:\n{name_source}")
        return

    report = folder / "rename_manifest.csv"

    highest_existing = max(
        find_highest_index(name_source),
        find_highest_index(folder),
    )

    start_index = highest_existing + 1

    images = sorted(
        [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
                and not GEN_PATTERN.match(path.stem)
            )
        ],
        key=lambda p: p.name.lower()
    )

    print(f"\nFound {len(images):,} images to rename.")
    print(f"Highest existing gen ID: {highest_existing:06d}")
    print(f"Starting at: gen_{start_index:06d}")
    print(f"Manifest: {report}")

    confirmation = input("\nProceed? [Y/n]: ").strip().lower()

    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    rows = []

    for index, old_path in enumerate(images, start=start_index):
        new_name = f"gen_{index:06d}{old_path.suffix.lower()}"
        new_path = folder / new_name

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

    # Temporary rename stage prevents collisions.
    temporary_paths = []

    for temp_index, (old_path, row) in enumerate(
        zip(images, rows),
        start=1
    ):
        temp_path = (
            folder
            / f"__rename_temp_{temp_index:06d}{old_path.suffix.lower()}"
        )

        old_path.rename(temp_path)

        temporary_paths.append(
            (temp_path, folder / row["new_filename"])
        )

    for temp_path, final_path in temporary_paths:
        temp_path.rename(final_path)

    with open(
        report,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:
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
    print(f"Manifest:\n{report}")


if __name__ == "__main__":
    main()