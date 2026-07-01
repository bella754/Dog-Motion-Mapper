"""
This file should only improve the keypoint visibility
It changes the color of the keypoint dots and sclae them to make them bigger
"""
import bpy

COLLECTION_NAME = "DLC_Keypoints"

coll = bpy.data.collections.get(COLLECTION_NAME)

if coll is None:
    raise ValueError("Collection DLC_Keypoints nicht gefunden.")

mat = bpy.data.materials.get("DLC_Keypoint_Bright")
if mat is None:
    mat = bpy.data.materials.new("DLC_Keypoint_Bright")
    mat.diffuse_color = (1.0, 1.0, 0.0, 1.0)

for obj in coll.objects:
    obj.scale = (2.0, 2.0, 2.0)
    obj.show_in_front = True

    if obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(mat)