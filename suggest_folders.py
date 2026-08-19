from pathlib import Path
from PIL import Image
import csv
import clip
import torch
import numpy as np
from collections import defaultdict

PROJECT_ROOT = Path.home() / "tools/image_deduper"
ORGANISED = Path("/mnt/c/Users/Danvx/My Stuff/Character Engine")
NEW_IMAGES = Path("/mnt/c/Users/Danvx/Desktop/GPT Images - NEW ONLY")
OUTPUT = PROJECT_ROOT / "_dedupe_results/folder_suggestions_centroid.csv"

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

# Conservative starting values.
UNKNOWN_THRESHOLD = 0.60
AMBIGUITY_MARGIN = 0.03


def image_files(root):
    return [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]


def folder_label(path):
    return str(path.parent.relative_to(ORGANISED))


device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {device}")
print("Loading CLIP model...")

model, preprocess = clip.load("ViT-B/32", device=device)

organised_files = image_files(ORGANISED)
new_files = image_files(NEW_IMAGES)

print(f"Organised images: {len(organised_files):,}")
print(f"New images: {len(new_files):,}")


def embed_images(files, label):
    embeddings = []
    valid_files = []

    for i, path in enumerate(files, start=1):
        try:
            image = preprocess(
                Image.open(path).convert("RGB")
            ).unsqueeze(0).to(device)

            with torch.no_grad():
                embedding = model.encode_image(image)

            embedding /= embedding.norm(dim=-1, keepdim=True)

            embeddings.append(embedding.cpu().numpy()[0])
            valid_files.append(path)

            if i % 100 == 0:
                print(f"{label}: {i:,}/{len(files):,}")

        except Exception as e:
            print(f"ERROR: {path}")
            print(e)

    return np.array(embeddings), valid_files


print("\nEmbedding organised archive...")

organised_embeddings, organised_files = embed_images(
    organised_files,
    "Organised"
)

print("\nBuilding folder centroids...")

folder_embeddings = defaultdict(list)
folder_files = defaultdict(list)

for path, embedding in zip(organised_files, organised_embeddings):
    label = folder_label(path)
    folder_embeddings[label].append(embedding)
    folder_files[label].append(path)


centroid_labels = []
centroids = []

for label, embeddings in folder_embeddings.items():
    centroid = np.mean(embeddings, axis=0)

    # Re-normalise the average vector.
    centroid /= np.linalg.norm(centroid)

    centroid_labels.append(label)
    centroids.append(centroid)

centroids = np.array(centroids)

print(f"Folder centroids: {len(centroid_labels):,}")


print("\nEmbedding new images...")

new_embeddings, new_files = embed_images(
    new_files,
    "New"
)


print("\nClassifying new images...")

rows = []

for i, (new_path, new_embedding) in enumerate(
    zip(new_files, new_embeddings),
    start=1
):
    # Compare new image to every folder centroid.
    folder_similarities = centroids @ new_embedding

    order = np.argsort(folder_similarities)[::-1]

    best_index = order[0]
    second_index = order[1]

    best_folder = centroid_labels[best_index]
    second_folder = centroid_labels[second_index]

    best_score = float(folder_similarities[best_index])
    second_score = float(folder_similarities[second_index])

    margin = best_score - second_score

    # Also find the closest individual organised image.
    individual_similarities = organised_embeddings @ new_embedding
    closest_index = int(np.argmax(individual_similarities))

    closest_image = organised_files[closest_index]
    closest_score = float(individual_similarities[closest_index])

    if best_score < UNKNOWN_THRESHOLD:
        status = "Unknown"
        suggestion = "Unknown"

    elif margin < AMBIGUITY_MARGIN:
        status = "Needs Review"
        suggestion = best_folder

    else:
        status = "Confident"
        suggestion = best_folder

    rows.append({
        "new_file": str(new_path),
        "status": status,
        "suggested_folder": suggestion,
        "centroid_score": round(best_score, 4),
        "second_folder": second_folder,
        "second_score": round(second_score, 4),
        "margin": round(margin, 4),
        "closest_existing_image": str(closest_image),
        "closest_similarity": round(closest_score, 4),
        "folder_example_count": len(folder_files[best_folder]),
    })

    if i % 100 == 0:
        print(f"Classified {i:,}/{len(new_files):,}")


OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with open(
    OUTPUT,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "new_file",
            "status",
            "suggested_folder",
            "centroid_score",
            "second_folder",
            "second_score",
            "margin",
            "closest_existing_image",
            "closest_similarity",
            "folder_example_count",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


print("\nDONE")
print(f"Suggestions written to:\n{OUTPUT}")