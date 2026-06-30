# Dog mesh pipeline using mouseModelSeminar RBF deformation

1. dog mesh model .blend in blender öffnen
2. in blender file->export-> as .obj exportieren
3. dog_dlc_singleview_to_coords3d.py ausführen 
python dog_dlc_singleview_to_coords3d.py \
  --dlc /PFAD/ZU/DEINER_DLC_DATEI.h5 \
  --video /PFAD/ZU/DEINEM_ORIGINAL_VIDEO.mp4 \
  --fps 30 \
  --individual animal0 \
  --pcutoff 0.6 \
  --keep-bodyparts back_base,back_middle,back_end,front_left_paw,front_right_paw,back_left_paw,back_right_paw,nose \
  --smooth-window 7 \
  --scale 0.001 \
  --out dog_coords_3d.csv

4. make_front_camera_json.py ausführen
python make_front_camera_json.py \
  --video /PFAD/ZU/DEINEM_ORIGINAL_VIDEO.mp4 \
  --scale 0.001 \
  --out dog_cameras.json

5. simulation starten in richtgien git repo (also ordner wechseln zu projects/mouseModelSeminar)
PYOPENGL_PLATFORM=egl python mouse_sim/mouse_deform_render_multi_swaprb.py \
  --mesh /home/bellatrix/master_cs/semester3/HTCV/project/dog_mesh_pipeline/dog_single_test_v2.obj \
  --mesh-nodes /home/bellatrix/master_cs/semester3/HTCV/project/dog_mesh_pipeline/dog_mesh_nodes.txt \
  --coords-3d /home/bellatrix/master_cs/semester3/HTCV/project/dog_mesh_pipeline/dog_coords_3d_body_stabilized.csv \
  --cameras /home/bellatrix/master_cs/semester3/HTCV/project/dog_mesh_pipeline/dog_cameras.json \
  --out-dir /home/bellatrix/master_cs/semester3/HTCV/project/dog_mesh_pipeline/dog_render_test_stabilized_fullbody \
  --mouse-ids 0 \
  --fps 30 \
  --kernel linear \
  --anchors 8 \
  --rigid-fit-nodes back_base,back_middle,back_end,nose \
  --start-frame 40 \
  --end-frame 110

