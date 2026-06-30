import csv
from pathlib import Path

import bpy


CSV_PATH = Path("/home/bellatrix/master_cs/semester3/HTCV/project/outputs/single_dog/singleDog_animal0_keypoints.csv")

SCALE = 0.005
Y_FLIP = True
FRAME_OFFSET = 0

# Erstmal nur die wichtigsten Punkte importieren
BODY_PARTS_TO_IMPORT = {
    "nose",
    "neck_base",
    "neck_end",
    "back_base",
    "back_middle",
    "back_end",
    "tail_base",
    "tail_end",
    "front_left_paw",
    "front_right_paw",
    "back_left_paw",
    "back_right_paw",
}


def get_or_create_empty(name):
    obj = bpy.data.objects.get(name)

    if obj is None:
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = "SPHERE"
        obj.empty_display_size = 0.05
        bpy.context.scene.collection.objects.link(obj)

    return obj


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    created = set()
    max_frame = 0

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            frame = int(row["frame"]) + FRAME_OFFSET
            bodypart = row["bodypart"]

            if bodypart not in BODY_PARTS_TO_IMPORT:
                continue

            x = float(row["x"])
            y = float(row["y"])

            # 2D image coordinates -> simple Blender plane
            blender_x = x * SCALE
            blender_y = 0.0
            blender_z = -y * SCALE if Y_FLIP else y * SCALE

            obj = get_or_create_empty(f"kp_{bodypart}")
            obj.location = (blender_x, blender_y, blender_z)
            obj.keyframe_insert(data_path="location", frame=frame)

            created.add(obj.name)
            max_frame = max(max_frame, frame)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = max_frame

    print("Imported keypoints:")
    for name in sorted(created):
        print(" ", name)
    print("End frame:", max_frame)


main()
