"""
This file was created by ChatGPT with all necessary informaion from my side
"""

import bpy
import csv
import re
from pathlib import Path
from collections import defaultdict


# ============================================================
# EINSTELLUNGEN
# ============================================================

CSV_PATH = r"/home/bellatrix/master_cs/semester3/HTCV/Dog-Motion-Mapper/dlc-outputs/single_dog/singleDog_animal0_keypoints.csv"

COLLECTION_NAME = "DLC_Keypoints"

FRAME_START = 1

SCALE = 0.01
X_OFFSET = 960.0
Y_OFFSET = 540.0

INVERT_IMAGE_Y = True
DEPTH_Y = 0.0

MIN_LIKELIHOOD = 0.1
POINT_RADIUS = 0.05

DELETE_OLD_KEYPOINTS = True

MAX_FRAMES = None


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def safe_name(name):
    name = str(name).strip()
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    return name.strip("_")


def to_float(value):
    value = str(value).strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def csv_to_blender_location(x_px, y_px):
    x = (x_px - X_OFFSET) * SCALE

    if INVERT_IMAGE_Y:
        z = -(y_px - Y_OFFSET) * SCALE
    else:
        z = (y_px - Y_OFFSET) * SCALE

    y = DEPTH_Y

    return (x, y, z)


def create_keypoint_object(name, collection, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=16,
        ring_count=8,
        radius=POINT_RADIUS,
        location=(0, 0, 0)
    )

    obj = bpy.context.object
    obj.name = f"kp_{safe_name(name)}"
    obj.data.name = f"{obj.name}_mesh"
    obj.data.materials.append(material)

    collection.objects.link(obj)

    for c in list(obj.users_collection):
        if c != collection:
            c.objects.unlink(obj)

    return obj


def set_visibility_keyframe(obj, frame, visible):
    obj.hide_viewport = not visible
    obj.hide_render = not visible
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.keyframe_insert(data_path="hide_render", frame=frame)


# ============================================================
# CSV LADEN
# ============================================================

csv_path = Path(CSV_PATH)

if not csv_path.exists():
    raise FileNotFoundError(f"CSV-Datei nicht gefunden: {csv_path}")

tracks = defaultdict(dict)

with open(csv_path, "r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    expected_columns = {"frame", "animal", "bodypart", "x", "y", "likelihood"}

    if not expected_columns.issubset(set(reader.fieldnames)):
        raise ValueError(
            f"CSV hat nicht die erwarteten Spalten. "
            f"Gefunden: {reader.fieldnames}"
        )

    for row in reader:
        frame_idx = int(float(row["frame"]))
        bodypart = row["bodypart"].strip()

        x = to_float(row["x"])
        y = to_float(row["y"])
        likelihood = to_float(row["likelihood"])

        if x is None or y is None:
            continue

        if likelihood is None:
            likelihood = 1.0

        # Falls derselbe Keypoint im selben Frame mehrfach vorkommt:
        # den mit höherer likelihood behalten.
        old = tracks[bodypart].get(frame_idx)

        if old is None or likelihood > old[2]:
            tracks[bodypart][frame_idx] = (x, y, likelihood)


if not tracks:
    raise ValueError("Keine Keypoints aus CSV gelesen.")

print("Gefundene Keypoints:", len(tracks))
for name in sorted(tracks.keys()):
    print("  ", name)


# ============================================================
# OPTIONAL: AUF MAX_FRAMES BEGRENZEN
# ============================================================

all_original_frames = sorted({frame for data in tracks.values() for frame in data.keys()})

if MAX_FRAMES is not None:
    allowed_frames = set(all_original_frames[:MAX_FRAMES])

    filtered_tracks = defaultdict(dict)

    for bodypart, frame_data in tracks.items():
        for frame_idx, values in frame_data.items():
            if frame_idx in allowed_frames:
                filtered_tracks[bodypart][frame_idx] = values

    tracks = filtered_tracks


all_frame_indices = sorted({frame for data in tracks.values() for frame in data.keys()})

min_frame_idx = min(all_frame_indices)
max_frame_idx = max(all_frame_indices)


# ============================================================
# ALTE COLLECTION LÖSCHEN
# ============================================================

if DELETE_OLD_KEYPOINTS:
    old_collection = bpy.data.collections.get(COLLECTION_NAME)

    if old_collection:
        for obj in list(old_collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        bpy.data.collections.remove(old_collection)


# ============================================================
# COLLECTION UND MATERIAL ERSTELLEN
# ============================================================

collection = bpy.data.collections.new(COLLECTION_NAME)
bpy.context.scene.collection.children.link(collection)

material = bpy.data.materials.new("DLC_Keypoint_Material")
material.diffuse_color = (1.0, 0.15, 0.05, 1.0)


# ============================================================
# KEYPOINT-OBJEKTE ERSTELLEN
# ============================================================

objects_by_keypoint = {}

for bodypart in sorted(tracks.keys()):
    obj = create_keypoint_object(bodypart, collection, material)
    objects_by_keypoint[bodypart] = obj


# ============================================================
# ANIMATION ERSTELLEN
# ============================================================

for bodypart, frame_data in tracks.items():
    obj = objects_by_keypoint[bodypart]

    for original_frame in range(min_frame_idx, max_frame_idx + 1):
        blender_frame = FRAME_START + (original_frame - min_frame_idx)

        if original_frame not in frame_data:
            set_visibility_keyframe(obj, blender_frame, False)
            continue

        x, y, likelihood = frame_data[original_frame]

        if likelihood < MIN_LIKELIHOOD:
            set_visibility_keyframe(obj, blender_frame, False)
            continue

        obj.location = csv_to_blender_location(x, y)
        obj.keyframe_insert(data_path="location", frame=blender_frame)
        set_visibility_keyframe(obj, blender_frame, True)


# ============================================================
# TIMELINE SETZEN
# ============================================================

bpy.context.scene.frame_start = FRAME_START
bpy.context.scene.frame_end = FRAME_START + (max_frame_idx - min_frame_idx)
bpy.context.scene.frame_set(FRAME_START)

print("--------------------------------------------------")
print("Import fertig.")
print("CSV:", csv_path)
print("Keypoints:", len(tracks))
print("Original frame range:", min_frame_idx, "-", max_frame_idx)
print("Blender frame range:", bpy.context.scene.frame_start, "-", bpy.context.scene.frame_end)
print("Collection:", COLLECTION_NAME)
print("--------------------------------------------------")