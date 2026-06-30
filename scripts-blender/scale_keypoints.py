import bpy

PARENT_NAME = "DLC_Keypoints_Transform"

# 1.0 = aktuelle Originalgröße
# 0.8 = 80%
# 0.5 = halb so groß
# 1.2 = größer
NEW_SCALE = 0.6

parent = bpy.data.objects.get(PARENT_NAME)

if parent is None:
    raise ValueError(f"{PARENT_NAME} nicht gefunden.")

parent.scale = (NEW_SCALE, NEW_SCALE, NEW_SCALE)

bpy.context.view_layer.update()

print(f"{PARENT_NAME} wurde auf Scale {NEW_SCALE} gesetzt.")