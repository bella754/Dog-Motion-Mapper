import bpy


# ============================================================
# EINSTELLUNGEN
# ============================================================

ARMATURE_NAME = "Arm_Shepherd"

# Erst niedrige Influence testen.
# 0.0 = kein Effekt
# 0.4 = sanfter Effekt
# 1.0 = Bone folgt komplett dem Keypoint
INFLUENCE = 0.4

MAPPING = {
    "Helper_shin_f.L": "kp_front_left_paw",
    "Helper_shin_f.R": "kp_front_right_paw",
    "Helper_foot_b.L": "kp_back_left_paw",
    "Helper_foot_b.R": "kp_back_right_paw",
}


# ============================================================
# ARMATURE HOLEN
# ============================================================

arm = bpy.data.objects.get(ARMATURE_NAME)

if arm is None:
    raise ValueError(f"Armature nicht gefunden: {ARMATURE_NAME}")

if arm.type != "ARMATURE":
    raise ValueError(f"{ARMATURE_NAME} ist keine Armature.")


# ============================================================
# CONSTRAINTS SETZEN
# ============================================================

for bone_name, kp_name in MAPPING.items():
    if bone_name not in arm.pose.bones:
        print("Bone nicht gefunden:", bone_name)
        continue

    kp = bpy.data.objects.get(kp_name)

    if kp is None:
        print("Keypoint nicht gefunden:", kp_name)
        continue

    pbone = arm.pose.bones[bone_name]

    # Alte DLC-Constraints entfernen
    for con in list(pbone.constraints):
        if con.name.startswith("DLC_CopyLocation_"):
            pbone.constraints.remove(con)

    con = pbone.constraints.new(type="COPY_LOCATION")
    con.name = "DLC_CopyLocation_" + kp_name
    con.target = kp
    con.target_space = "WORLD"
    con.owner_space = "WORLD"
    con.influence = INFLUENCE

    print(f"{bone_name} folgt {kp_name} mit Influence {INFLUENCE}")

bpy.context.view_layer.update()

print("Pfoten-Constraints gesetzt.")