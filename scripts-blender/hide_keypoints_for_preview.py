import bpy

KEYPOINT_COLLECTION = "DLC_Keypoints"

coll = bpy.data.collections.get(KEYPOINT_COLLECTION)

if coll is None:
    raise ValueError(f"Collection nicht gefunden: {KEYPOINT_COLLECTION}")

for obj in coll.objects:
    # Alte Visibility-Keyframes entfernen
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        for fc in list(action.fcurves):
            if fc.data_path in {"hide_viewport", "hide_render"}:
                action.fcurves.remove(fc)

    obj.hide_viewport = True
    obj.hide_render = True

print("Keypoints wurden aus Viewport und Render ausgeblendet.")

"""
# To show the keypoints again

import bpy

KEYPOINT_COLLECTION = "DLC_Keypoints"

coll = bpy.data.collections.get(KEYPOINT_COLLECTION)

if coll is None:
    raise ValueError(f"Collection nicht gefunden: {KEYPOINT_COLLECTION}")

for obj in coll.objects:
    # Alte Visibility-Keyframes entfernen
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        for fc in list(action.fcurves):
            if fc.data_path in {"hide_viewport", "hide_render"}:
                action.fcurves.remove(fc)

    obj.hide_viewport = True
    obj.hide_render = True

print("Keypoints wurden aus Viewport und Render ausgeblendet.")
"""