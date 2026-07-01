"""
influence:
0.05 - 0.15 = sehr vorsichtig
0.2  - 0.35 = sichtbar, aber noch halbwegs stabil
1.0         = fast nie für diese restlichen Punkte sinnvoll

use_z:
True  = Höhe folgt mit
False = nur X/Y, stabiler
"""
import bpy

# base settings
ARMATURE_NAME = "Arm_Shepherd"

LOCKED_BONES = {
    "Spine_04",
    "Helper_shin_f.L",
    "Helper_shin_f.R",
    "Helper_foot_b.L",
    "Helper_foot_b.R",
}

REMOVE_OLD_DLC_CONSTRAINTS = True

SWAP_LEFT_RIGHT = False

SPECS = [
    {
        "label": "back_base_to_spine_base",
        "bones": ["Spine_base", "Spine_01", "Root_bone"],
        "keypoints": ["kp_back_base"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": False,
    },
    {
        "label": "back_end_to_spine_05",
        "bones": ["Spine_05", "Spine_03", "Spine_02"],
        "keypoints": ["kp_back_end"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": False,
    },
    {
        "label": "neck_to_neck_keypoint",
        "bones": ["neck", "Neck", "Neck_01", "Spine_05"],
        "keypoints": ["kp_neck_base", "kp_neck", "kp_throat", "kp_back_base"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "head_to_head_keypoint",
        "bones": ["head", "Head"],
        "keypoints": ["kp_head", "kp_nose", "kp_left_eye", "kp_right_eye"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "mouth_to_nose",
        "bones": ["mouth", "Mouth", "jaw", "Jaw"],
        "keypoints": ["kp_mouth", "kp_nose"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "front_left_knee",
        "bones": ["shin_f.L", "forearm_f.L", "lower_arm_f.L", "leg_f.L"],
        "keypoints": ["kp_front_left_knee"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "front_right_knee",
        "bones": ["shin_f.R", "forearm_f.R", "lower_arm_f.R", "leg_f.R"],
        "keypoints": ["kp_front_right_knee"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "front_left_thai",
        "bones": ["thigh_f.L", "upper_arm_f.L", "shoulder_f.L"],
        "keypoints": ["kp_front_left_thai", "kp_front_left_thigh"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "front_right_thai",
        "bones": ["thigh_f.R", "upper_arm_f.R", "shoulder_f.R"],
        "keypoints": ["kp_front_right_thai", "kp_front_right_thigh"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "back_left_knee",
        "bones": ["shin_b.L", "Helper_shin_b.L", "lower_leg_b.L", "leg_b.L"],
        "keypoints": ["kp_back_left_knee"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "back_right_knee",
        "bones": ["shin_b.R", "Helper_shin_b.R", "lower_leg_b.R", "leg_b.R"],
        "keypoints": ["kp_back_right_knee"],
        "influence": 0.20,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "back_left_thai",
        "bones": ["thigh_b.L", "upper_leg_b.L", "hip_b.L"],
        "keypoints": ["kp_back_left_thai", "kp_back_left_thigh"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "back_right_thai",
        "bones": ["thigh_b.R", "upper_leg_b.R", "hip_b.R"],
        "keypoints": ["kp_back_right_thai", "kp_back_right_thigh"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "body_middle_left",
        "bones": ["body_middle.L", "rib.L", "chest.L", "Spine_03"],
        "keypoints": ["kp_body_middle_left"],
        "influence": 0.08,
        "use_x": True,
        "use_y": True,
        "use_z": False,
    },
    {
        "label": "body_middle_right",
        "bones": ["body_middle.R", "rib.R", "chest.R", "Spine_03"],
        "keypoints": ["kp_body_middle_right"],
        "influence": 0.08,
        "use_x": True,
        "use_y": True,
        "use_z": False,
    },
    {
        "label": "tail_base",
        "bones": ["tail_base", "Tail_base", "tail_01", "Tail_01"],
        "keypoints": ["kp_tail_base", "kp_back_end"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
    {
        "label": "tail_end",
        "bones": ["tail_end", "Tail_end", "tail_03", "Tail_03", "tail_04", "Tail_04"],
        "keypoints": ["kp_tail_end"],
        "influence": 0.15,
        "use_x": True,
        "use_y": True,
        "use_z": True,
    },
]

# helper
def maybe_swap_lr(name):
    if not SWAP_LEFT_RIGHT:
        return name

    # Nur für Keypoint-Namen anwenden.
    if "_left_" in name:
        return name.replace("_left_", "_right_")
    if "_right_" in name:
        return name.replace("_right_", "_left_")
    if name.endswith("_left"):
        return name[:-5] + "_right"
    if name.endswith("_right"):
        return name[:-6] + "_left"

    return name


def first_existing_bone(arm, names):
    for name in names:
        if name in LOCKED_BONES:
            continue
        if name in arm.pose.bones:
            return name
    return None


def first_existing_keypoint(names):
    for name in names:
        swapped = maybe_swap_lr(name)
        obj = bpy.data.objects.get(swapped)
        if obj is not None:
            return swapped, obj
    return None, None


def add_copy_location_constraint(pbone, target, spec):
    if REMOVE_OLD_DLC_CONSTRAINTS:
        for con in list(pbone.constraints):
            if con.name.startswith("DLC_Remaining_"):
                pbone.constraints.remove(con)

    con = pbone.constraints.new(type="COPY_LOCATION")
    con.name = "DLC_Remaining_" + spec["label"]
    con.target = target
    con.target_space = "WORLD"
    con.owner_space = "WORLD"

    con.use_x = spec.get("use_x", True)
    con.use_y = spec.get("use_y", True)
    con.use_z = spec.get("use_z", True)

    con.influence = spec.get("influence", 0.1)

    return con

# get mesh obj
arm = bpy.data.objects.get(ARMATURE_NAME)

if arm is None:
    raise ValueError(f"Armature nicht gefunden: {ARMATURE_NAME}")

if arm.type != "ARMATURE":
    raise ValueError(f"{ARMATURE_NAME} ist keine Armature.")


# actual mapping
mapped = []
skipped = []

for spec in SPECS:
    label = spec["label"]

    bone_name = first_existing_bone(arm, spec["bones"])
    kp_name, kp_obj = first_existing_keypoint(spec["keypoints"])

    if bone_name is None:
        skipped.append((label, "kein passender Bone gefunden", spec["bones"]))
        continue

    if kp_obj is None:
        skipped.append((label, "kein passender Keypoint gefunden", spec["keypoints"]))
        continue

    pbone = arm.pose.bones[bone_name]

    con = add_copy_location_constraint(pbone, kp_obj, spec)

    mapped.append((label, bone_name, kp_name, con.influence, con.use_x, con.use_y, con.use_z))

    print(
        f"OK: {label}: {bone_name} -> {kp_name} "
        f"| influence={con.influence} "
        f"| axes X={con.use_x} Y={con.use_y} Z={con.use_z}"
    )


print("--------------------------------------------------")
print("Gemappt:", len(mapped))
print("Übersprungen:", len(skipped))

if skipped:
    print("--------------------------------------------------")
    print("Übersprungene Mappings:")
    for label, reason, candidates in skipped:
        print(f"- {label}: {reason}")
        print("  Kandidaten:", candidates)

bpy.context.view_layer.update()