import bpy
from pathlib import Path

# base settings
TEXTURE_DIR = Path("/home/bellatrix/master_cs/semester3/HTCV/mesh_model/shepperd/Shepherd_Textures_v01/texture")

DOG_MESH_NAME = "Shepherd"

# Falls Albedo1 nicht gut aussieht, später 2 oder 3 testen.
MAIN_ALBEDO = "Shepherd_Albedo1.png"

AO_TEXTURE = "Shepherd_AO.png"
NORMAL_TEXTURE = "Shepherd_Normal.png"
ROUGHNESS_TEXTURE = "Shepherd_Roughness.png"

# texture path
albedo_path = TEXTURE_DIR / MAIN_ALBEDO
ao_path = TEXTURE_DIR / AO_TEXTURE
normal_path = TEXTURE_DIR / NORMAL_TEXTURE
roughness_path = TEXTURE_DIR / ROUGHNESS_TEXTURE

for path in [albedo_path, ao_path, normal_path, roughness_path]:
    if not path.exists():
        raise FileNotFoundError(f"Textur nicht gefunden: {path}")

# get mesh object
dog = bpy.data.objects.get(DOG_MESH_NAME)

if dog is None:
    raise ValueError(f"Mesh-Objekt nicht gefunden: {DOG_MESH_NAME}")

if dog.type != "MESH":
    raise ValueError(f"{DOG_MESH_NAME} ist kein Mesh-Objekt.")


# create material
mat_name = "Shepherd_Textured_Material"

old_mat = bpy.data.materials.get(mat_name)
if old_mat is not None:
    bpy.data.materials.remove(old_mat, do_unlink=True)

mat = bpy.data.materials.new(mat_name)
mat.use_nodes = True

nodes = mat.node_tree.nodes
links = mat.node_tree.links

nodes.clear()

# Output
output = nodes.new(type="ShaderNodeOutputMaterial")
output.location = (800, 0)

# Principled BSDF
bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
bsdf.location = (450, 0)

# Albedo / Base Color
tex_albedo = nodes.new(type="ShaderNodeTexImage")
tex_albedo.location = (-700, 250)
tex_albedo.image = bpy.data.images.load(str(albedo_path), check_existing=True)
tex_albedo.image.colorspace_settings.name = "sRGB"

# AO
tex_ao = nodes.new(type="ShaderNodeTexImage")
tex_ao.location = (-700, 0)
tex_ao.image = bpy.data.images.load(str(ao_path), check_existing=True)
tex_ao.image.colorspace_settings.name = "Linear"

# Albedo * AO
mix_ao = nodes.new(type="ShaderNodeMixRGB")
mix_ao.location = (-250, 180)
mix_ao.blend_type = "MULTIPLY"
mix_ao.inputs["Fac"].default_value = 0.7

# Roughness
tex_rough = nodes.new(type="ShaderNodeTexImage")
tex_rough.location = (-700, -250)
tex_rough.image = bpy.data.images.load(str(roughness_path), check_existing=True)
tex_rough.image.colorspace_settings.name = "Linear"

# Normal
tex_normal = nodes.new(type="ShaderNodeTexImage")
tex_normal.location = (-700, -500)
tex_normal.image = bpy.data.images.load(str(normal_path), check_existing=True)
tex_normal.image.colorspace_settings.name = "Linear"

normal_map = nodes.new(type="ShaderNodeNormalMap")
normal_map.location = (-250, -500)
normal_map.inputs["Strength"].default_value = 0.6

# Links
links.new(tex_albedo.outputs["Color"], mix_ao.inputs[1])
links.new(tex_ao.outputs["Color"], mix_ao.inputs[2])
links.new(mix_ao.outputs["Color"], bsdf.inputs["Base Color"])

links.new(tex_rough.outputs["Color"], bsdf.inputs["Roughness"])

links.new(tex_normal.outputs["Color"], normal_map.inputs["Color"])
links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

# Material etwas weniger glänzend
if "Specular" in bsdf.inputs:
    bsdf.inputs["Specular"].default_value = 0.25

# set texture
dog.data.materials.clear()
dog.data.materials.append(mat)

bpy.context.view_layer.update()