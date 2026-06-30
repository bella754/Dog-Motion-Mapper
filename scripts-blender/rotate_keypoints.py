import bpy
import math
from mathutils import Matrix


# ============================================================
# EINSTELLUNGEN
# ============================================================

KEYPOINT_COLLECTION = "DLC_Keypoints"
PARENT_NAME = "DLC_Keypoints_Transform"

# Erst 90 testen.
# Wenn die Punkte danach von dir weg statt auf dich zu laufen: -90 nehmen.
ROT_Z_DEGREES = 90.0
# ROT_Z_DEGREES = -90.0

# Anchor-Punkt, um den rotiert wird.
# back_middle ist meistens sinnvoll.
ANCHOR_KEYPOINT = "kp_back_middle"


# ============================================================
# OBJEKTE HOLEN
# ============================================================

coll = bpy.data.collections.get(KEYPOINT_COLLECTION)
if coll is None:
    raise ValueError(f"Collection nicht gefunden: {KEYPOINT_COLLECTION}")

anchor = bpy.data.objects.get(ANCHOR_KEYPOINT)
if anchor is None:
    raise ValueError(f"Anchor-Keypoint nicht gefunden: {ANCHOR_KEYPOINT}")


# ============================================================
# ALTES TRANSFORM-EMPTY ENTFERNEN, FALLS VORHANDEN
# ============================================================

old_parent = bpy.data.objects.get(PARENT_NAME)

if old_parent is not None:
    for obj in list(bpy.data.objects):
        if obj.parent == old_parent:
            world_matrix = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = world_matrix

    bpy.data.objects.remove(old_parent, do_unlink=True)


# ============================================================
# NEUES EMPTY AM ANCHOR ERSTELLEN
# ============================================================

bpy.context.view_layer.update()

anchor_world = anchor.matrix_world.translation.copy()

bpy.ops.object.empty_add(type="PLAIN_AXES", location=anchor_world)
parent = bpy.context.object
parent.name = PARENT_NAME


# ============================================================
# KEYPOINTS AN EMPTY HÄNGEN, ABER WORLD-POSITION BEHALTEN
# ============================================================

for obj in coll.objects:
    if obj == parent:
        continue

    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix


# ============================================================
# GRUPPE ROTIEREN
# ============================================================

parent.rotation_euler = (
    0.0,
    0.0,
    math.radians(ROT_Z_DEGREES)
)

bpy.context.view_layer.update()

print("Keypoints rotiert.")
print("Rotation Z:", ROT_Z_DEGREES)
print("Anchor:", ANCHOR_KEYPOINT)
print("Wenn die Richtung falsch ist, ROT_Z_DEGREES auf -90.0 setzen und Script erneut ausführen.")