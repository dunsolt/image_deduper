from pathlib import Path
from PIL import Image
import hashlib
import csv


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

DEFAULT_ORGANISED = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")
DEFAULT_OUTPUT_ROOT = Path.home() / "tools/image_deduper/_dedupe_results"


def ask_path(prompt, default=None):
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        path = Path(value) if value else default
    else:
        value = input(f"{prompt}: ").strip()
        path = Path(value)

    return path.expanduser()


def image_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def count_images(root: Path):
    return sum(1 for _ in image_files(root))


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


def main():
    print("\n=== Image Deduper ===\n")

    organised = ask_path(
        "Character Engine folder",
        DEFAULT_ORGANISED,
    )

    new_batch = ask_path(
        "New batch folder"
    )

    batch_name = input("Batch name: ").strip()

    if not batch_name:
        print("Error: batch name cannot be empty.")
        return

    output = DEFAULT_OUTPUT_ROOT / batch_name

    if not organised.exists():
        print(f"\nError: Character Engine folder does not exist:\n{organised}")
        return

    if not new_batch.exists():
        print(f"\nError: new batch folder does not exist:\n{new_batch}")
        return

    if not organised.is_dir():
        print(f"\nError: Character Engine path is not a directory:\n{organised}")
        return

    if not new_batch.is_dir():
        print(f"\nError: new batch path is not a directory:\n{new_batch}")
        return

    print("\nChecking folders...")

    organised_count_preview = count_images(organised)
    new_batch_count_preview = count_images(new_batch)

    print(f"\nCharacter Engine: {organised_count_preview:,} images")
    print(f"New batch:        {new_batch_count_preview:,} images")
    print(f"Results folder:   {output}")

    confirmation = input("\nStart scan? [Y/n]: ").strip().lower()

    if confirmation not in ("", "y", "yes"):
        print("Cancelled.")
        return

    output.mkdir(parents=True, exist_ok=True)

    print("\nIndexing organised archive...")

    organised_hashes = {}
    organised_count = 0
    errors = []

    for path in image_files(organised):
        try:
            digest, dimensions = pixel_hash(path)

            organised_hashes.setdefault(digest, []).append({
                "path": path,
                "dimensions": dimensions,
            })

            organised_count += 1

            if organised_count % 250 == 0:
                print(
                    f"  Indexed {organised_count:,} organised images..."
                )

        except Exception as e:
            errors.append((str(path), str(e)))

    print(f"\nIndexed {organised_count:,} organised images.")
    print("\nComparing new batch...")

    matches = []
    new_images = []
    new_count = 0

    for path in image_files(new_batch):
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

    with open(
        output / "exact_pixel_matches.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
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

    with open(
        output / "new_images.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
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

    with open(
        output / "errors.csv",
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["file", "error"])
        writer.writerows(errors)

    print("\nDONE")
    print(f"Organised archive: {organised_count:,} images")
    print(f"New batch checked: {new_count:,} images")
    print(f"Pixel-identical matches: {len(matches):,}")
    print(f"Genuinely unmatched: {len(new_images):,}")
    print(f"Errors: {len(errors):,}")
    print(f"\nReports saved to:\n{output}")


if __name__ == "__main__":
    main()