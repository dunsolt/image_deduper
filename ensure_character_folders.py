from pathlib import Path

CHARACTER_ENGINE = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")

REQUIRED_SUBFOLDERS = {
    "OG",
    "Fortnite",
    "RPG",
    "References",
    "Videos",
}

SKIP_FOLDERS = {
    "Z Random",
}


def ensure_character_subfolders(root: Path):
    created = 0
    skipped_existing = 0

    for character_folder in root.iterdir():
        if not character_folder.is_dir():
            continue

        if character_folder.name in SKIP_FOLDERS:
            print(f"Skipping: {character_folder.name}")
            continue

        print(f"\nChecking: {character_folder.name}")

        for subfolder_name in REQUIRED_SUBFOLDERS:
            target = character_folder / subfolder_name

            if target.exists():
                if target.is_dir():
                    print(f"  Exists:  {subfolder_name}")
                    skipped_existing += 1
                    continue

                # Extra safety:
                # if a FILE somehow has the required folder name,
                # refuse to touch it.
                print(
                    f"  WARNING: '{subfolder_name}' exists but is not a folder."
                )
                continue

            target.mkdir()

            print(f"  Created: {subfolder_name}")
            created += 1

    print("\nDONE")
    print(f"Folders created: {created}")
    print(f"Existing folders left untouched: {skipped_existing}")


if __name__ == "__main__":
    ensure_character_subfolders(CHARACTER_ENGINE)