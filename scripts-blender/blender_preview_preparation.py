import bpy
from mathutils import Vector

# basic setup
ARMATURE_NAME = "Arm_Shepherd"
KEYPOINT_COLLECTION = "DLC_Keypoints"

OUTPUT_PATH = "/home/bellatrix/master_cs/semester3/HTCV/project/scripts-blender/dog_animation.mp4"

RESOLUTION_X = 1280
RESOLUTION_Y = 720
FPS = 30

CAMERA_OFFSET = Vector((0.0, -7.0, 3.0))

CAMERA_TARGET_Z_OFFSET = 1.0

ADD_SIMPLE_FUR = False

# helper functions
def collection_contains_object(collection_name, obj):
    coll = bpy.data.collections.get(collection_name)
    if coll is None:
        return False
    return obj.name in coll.objects


def get_dog_mesh_objects():
    meshes = []

    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue

        if collection_contains_object(KEYPOINT_COLLECTION, obj):
            continue

        if obj.name.startswith("Ground"):
            continue

        meshes.append(obj)

    return meshes


def get_world_bbox(objects):
    points = []

    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        return None, None

    min_v = Vector((
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points),
    ))

    max_v = Vector((
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points),
    ))

    return min_v, max_v


# hide keypoints
kp_coll = bpy.data.collections.get(KEYPOINT_COLLECTION)

if kp_coll is not None:
    for obj in kp_coll.objects:
        obj.hide_viewport = True
        obj.hide_render = True

print("Keypoints ausgeblendet.")

# get dog mesh
dog_meshes = get_dog_mesh_objects()

print("Dog mesh objects:")
for obj in dog_meshes:
    print("  ", obj.name)

bbox_min, bbox_max = get_world_bbox(dog_meshes)

if bbox_min is None:
    floor_z = 0.0
    center = Vector((0, 0, 0))
    size = 10.0
else:
    floor_z = bbox_min.z
    center = (bbox_min + bbox_max) / 2
    size = max(
        bbox_max.x - bbox_min.x,
        bbox_max.y - bbox_min.y,
        6.0
    ) * 3.0

# optional: brauche ich das? 
if ADD_SIMPLE_FUR:
    for obj in dog_meshes:
        if obj.type != "MESH":
            continue

        if "Simple_Fur" in obj.modifiers:
            continue

        mod = obj.modifiers.new("Simple_Fur", "PARTICLE_SYSTEM")
        ps = mod.particle_system.settings
        ps.type = "HAIR"
        ps.count = 1500
        ps.hair_length = 0.04
        ps.use_advanced_hair = True
        ps.render_type = "PATH"
        ps.use_modifier_stack = True
        ps.roughness_1_size = 0.01
        ps.roughness_2_size = 0.005

    print("Simple Fur hinzugefügt.")

# create ground
old_ground = bpy.data.objects.get("Ground_Basic")
if old_ground is not None:
    bpy.data.objects.remove(old_ground, do_unlink=True)

bpy.ops.mesh.primitive_plane_add(
    size=size,
    location=(center.x, center.y, floor_z - 0.01)
)

ground = bpy.context.object
ground.name = "Ground_Basic"

mat_ground = bpy.data.materials.get("Ground_Material")
if mat_ground is None:
    mat_ground = bpy.data.materials.new("Ground_Material")
    mat_ground.diffuse_color = (0.55, 0.55, 0.55, 1.0)

ground.data.materials.append(mat_ground)

# create light
old_light = bpy.data.objects.get("Main_Area_Light")
if old_light is not None:
    bpy.data.objects.remove(old_light, do_unlink=True)

bpy.ops.object.light_add(
    type="AREA",
    location=(center.x, center.y - 3.0, floor_z + 5.0)
)

light = bpy.context.object
light.name = "Main_Area_Light"
light.data.energy = 700
light.data.size = 5.0

# create camera / target
arm = bpy.data.objects.get(ARMATURE_NAME)

if arm is None:
    raise ValueError(f"Armature nicht gefunden: {ARMATURE_NAME}")

old_target = bpy.data.objects.get("Camera_Target")
if old_target is not None:
    bpy.data.objects.remove(old_target, do_unlink=True)

bpy.ops.object.empty_add(
    type="PLAIN_AXES",
    location=arm.location + Vector((0.0, 0.0, CAMERA_TARGET_Z_OFFSET))
)

target = bpy.context.object
target.name = "Camera_Target"
target.parent = arm
target.location = (0.0, 0.0, CAMERA_TARGET_Z_OFFSET)


old_camera = bpy.data.objects.get("Dog_Camera")
if old_camera is not None:
    bpy.data.objects.remove(old_camera, do_unlink=True)

bpy.ops.object.camera_add(
    location=arm.location + CAMERA_OFFSET,
    rotation=(0.0, 0.0, 0.0)
)

camera = bpy.context.object
camera.name = "Dog_Camera"
camera.data.lens = 35

constraint = camera.constraints.new(type="TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"

bpy.context.scene.camera = camera

# render setup
scene = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE"

if hasattr(scene, "eevee"):
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3
    scene.eevee.gtao_factor = 1.5

scene.render.resolution_x = RESOLUTION_X
scene.render.resolution_y = RESOLUTION_Y
scene.render.fps = FPS

scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.ffmpeg_preset = "GOOD"

scene.render.filepath = OUTPUT_PATH

# Viewport etwas schöner
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "RENDERED"