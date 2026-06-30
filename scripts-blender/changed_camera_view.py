import bpy
from mathutils import Vector


# ============================================================
# EINSTELLUNGEN
# ============================================================

ARMATURE_NAME = "Arm_Shepherd"

CAMERA_NAME = "Dog_Side_Camera"
TARGET_NAME = "Dog_Side_Camera_Target"

# Seite:
# +X = eine Seite
# -X = andere Seite
SIDE = "+X"
# SIDE = "-X"

# Abstand zur Laufbahn
DISTANCE = 5.0

# Kamerahöhe
HEIGHT = 1.2

# Zielhöhe: worauf die Kamera schaut
TARGET_HEIGHT = 0.8

# Brennweite:
# kleiner = mehr Umgebung sichtbar
# größer = näher/zoomed
LENS = 35

# Frames zum Abschätzen der Laufbahn
START_FRAME = bpy.context.scene.frame_start
END_FRAME = bpy.context.scene.frame_end


# ============================================================
# ARMATURE HOLEN
# ============================================================

scene = bpy.context.scene
arm = bpy.data.objects.get(ARMATURE_NAME)

if arm is None:
    raise ValueError(f"Armature nicht gefunden: {ARMATURE_NAME}")


# ============================================================
# LAUFBAHN / MITTELPUNKT BESTIMMEN
# ============================================================

positions = []

step = max(1, int((END_FRAME - START_FRAME) / 50))

for frame in range(START_FRAME, END_FRAME + 1, step):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    positions.append(arm.matrix_world.translation.copy())

if not positions:
    positions.append(arm.matrix_world.translation.copy())

min_x = min(p.x for p in positions)
max_x = max(p.x for p in positions)
min_y = min(p.y for p in positions)
max_y = max(p.y for p in positions)
min_z = min(p.z for p in positions)
max_z = max(p.z for p in positions)

center = Vector((
    (min_x + max_x) / 2,
    (min_y + max_y) / 2,
    (min_z + max_z) / 2,
))

target_location = Vector((
    center.x,
    center.y,
    TARGET_HEIGHT,
))


# ============================================================
# ALTE KAMERA / TARGET LÖSCHEN
# ============================================================

for name in [CAMERA_NAME, TARGET_NAME]:
    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)


# ============================================================
# TARGET ERSTELLEN
# ============================================================

bpy.ops.object.empty_add(
    type="PLAIN_AXES",
    location=target_location
)

target = bpy.context.object
target.name = TARGET_NAME


# ============================================================
# KAMERA SEITLICH ERSTELLEN
# ============================================================

side_sign = 1.0 if SIDE == "+X" else -1.0

camera_location = Vector((
    center.x + side_sign * DISTANCE,
    center.y,
    HEIGHT,
))

bpy.ops.object.camera_add(
    location=camera_location,
    rotation=(0, 0, 0)
)

camera = bpy.context.object
camera.name = CAMERA_NAME
camera.data.lens = LENS

# Kamera schaut auf festen Target-Punkt
con = camera.constraints.new(type="TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"

scene.camera = camera

# Zurück zum Startframe
scene.frame_set(START_FRAME)
bpy.context.view_layer.update()

print("Feste Seitenkamera gesetzt.")
print("Kamera:", CAMERA_NAME)
print("Side:", SIDE)
print("Location:", camera.location)
print("Target:", target.location)
print("Lens:", LENS)