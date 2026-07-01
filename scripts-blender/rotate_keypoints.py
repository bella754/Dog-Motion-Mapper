import bpy
import math
from mathutils import Matrix

# base settings
KEYPOINT_COLLECTION = "DLC_Keypoints"
PARENT_NAME = "DLC_Keypoints_Transform"
ROT_Z_DEGREES = 90.0
ANCHOR_KEYPOINT = "kp_back_middle"

# get obj
coll = bpy.data.collections.get(KEYPOINT_COLLECTION)
if coll is None:
    raise ValueError(f"Collection nicht gefunden: {KEYPOINT_COLLECTION}")

anchor = bpy.data.objects.get(ANCHOR_KEYPOINT)
if anchor is None:
    raise ValueError(f"Anchor-Keypoint nicht gefunden: {ANCHOR_KEYPOINT}")


# delete old settings
old_parent = bpy.data.objects.get(PARENT_NAME)

if old_parent is not None:
    for obj in list(bpy.data.objects):
        if obj.parent == old_parent:
            world_matrix = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = world_matrix

    bpy.data.objects.remove(old_parent, do_unlink=True)

# create new parent
bpy.context.view_layer.update()

anchor_world = anchor.matrix_world.translation.copy()

bpy.ops.object.empty_add(type="PLAIN_AXES", location=anchor_world)
parent = bpy.context.object
parent.name = PARENT_NAME

# append keypoints to parent
for obj in coll.objects:
    if obj == parent:
        continue

    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix

# rotate keypoints
parent.rotation_euler = (
    0.0,
    0.0,
    math.radians(ROT_Z_DEGREES)
)

bpy.context.view_layer.update()