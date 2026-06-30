import bpy


# ============================================================
# EINSTELLUNGEN
# ============================================================

ARMATURE_NAME = "Arm_Shepherd"

TARGET_KEYPOINT = "kp_back_middle"

ANCHOR_BONE = "Spine_04"

START_FRAME = bpy.context.scene.frame_start
END_FRAME = bpy.context.scene.frame_end

# Für deinen Fall: Keypoint-Hund kommt jetzt in Y-Richtung auf dich zu.
# X = links/rechts, Y = vor/zurück, Z = hoch/runter.
FOLLOW_X = True
FOLLOW_Y = True

# Erstmal False lassen, damit der Hund nicht komisch hoch/runter springt.
FOLLOW_Z = False


# ============================================================
# OBJEKTE HOLEN
# ============================================================

scene = bpy.context.scene

arm = bpy.data.objects.get(ARMATURE_NAME)
target = bpy.data.objects.get(TARGET_KEYPOINT)

if arm is None:
    raise ValueError(f"Armature nicht gefunden: {ARMATURE_NAME}")

if target is None:
    raise ValueError(f"Keypoint nicht gefunden: {TARGET_KEYPOINT}")

if arm.type != "ARMATURE":
    raise ValueError(f"{ARMATURE_NAME} ist keine Armature.")

if ANCHOR_BONE not in arm.pose.bones:
    raise ValueError(f"Bone nicht gefunden: {ANCHOR_BONE}")


def get_bone_head_world(armature_obj, bone_name):
    pbone = armature_obj.pose.bones[bone_name]
    return armature_obj.matrix_world @ pbone.head


def move_object_world(obj, delta):
    obj.location.x += delta.x
    obj.location.y += delta.y
    obj.location.z += delta.z


# ============================================================
# ALTE LOCATION-KEYFRAMES VOM ARMATURE-OBJEKT ENTFERNEN
# ============================================================

if arm.animation_data and arm.animation_data.action:
    action = arm.animation_data.action

    for fc in list(action.fcurves):
        if fc.data_path == "location":
            action.fcurves.remove(fc)


# ============================================================
# ARMATURE PRO FRAME AUF KEYPOINT SCHIEBEN
# ============================================================

for frame in range(START_FRAME, END_FRAME + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()

    bone_world = get_bone_head_world(arm, ANCHOR_BONE)
    target_world = target.matrix_world.translation.copy()

    delta = target_world - bone_world

    if not FOLLOW_X:
        delta.x = 0.0

    if not FOLLOW_Y:
        delta.y = 0.0

    if not FOLLOW_Z:
        delta.z = 0.0

    move_object_world(arm, delta)

    arm.keyframe_insert(data_path="location", frame=frame)


scene.frame_set(START_FRAME)
bpy.context.view_layer.update()

print("Fertig.")
print(f"{ARMATURE_NAME} wurde so animiert, dass {ANCHOR_BONE} {TARGET_KEYPOINT} folgt.")
print("Frames:", START_FRAME, "-", END_FRAME)