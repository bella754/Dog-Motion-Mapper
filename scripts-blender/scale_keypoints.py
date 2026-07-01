import bpy

PARENT_NAME = "DLC_Keypoints_Transform"
NEW_SCALE = 0.2

parent = bpy.data.objects.get(PARENT_NAME)

if parent is None:
    raise ValueError(f"{PARENT_NAME} nicht gefunden.")

parent.scale = (NEW_SCALE, NEW_SCALE, NEW_SCALE)

bpy.context.view_layer.update()