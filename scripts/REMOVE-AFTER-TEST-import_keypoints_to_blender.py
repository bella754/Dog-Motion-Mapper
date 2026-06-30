import csv
import bpy
from pathlib import Path


CSV_PATH = "/home/bellatrix/master_cs/semester3/HTCV/project/outputs/singleDog/single_dog_animal0_keypoints.csv"

SCALE = 0.01
Y_FLIP = True

FRAME_STEP = 1


def get_or_create_empty(name):
    obj = bpy.data.objects.get(name)

    if obj is None:
        bpy.ops.object.empty_add(type="SPHERE", location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.empty_display_size = 0.08

    return obj


def main():
    csv_path = Path(CSV_PATH)

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            frame = int(row["frame"])
            bodypart = row["bodypart"]

            x = float(row["x"])
            y = float(row["y"])

            blender_x = x * SCALE
            blender_y = -y * SCALE if Y_FLIP else y * SCALE
            blender_z = 0.0

            obj = get_or_create_empty(f"kp_{bodypart}")
            obj.location = (blender_x, blender_y, blender_z)
            obj.keyframe_insert(data_path="location", frame=frame * FRAME_STEP)

    print("Imported keypoints into Blender.")


main()