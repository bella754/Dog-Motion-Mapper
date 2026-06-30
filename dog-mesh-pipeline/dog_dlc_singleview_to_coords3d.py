#!/usr/bin/env python3
"""
Convert single-view DeepLabCut dog keypoints to the coords_3d.csv format expected by
mouse_sim/mouse_deform_render_multi_swaprb.py.

This creates a pseudo-3D side-view coordinate system:
  X = image x * scale
  Y = constant depth (default 0)
  Z = (image_height - image y) * scale

This is NOT true 3D reconstruction. It is intended as a first prototype for driving
an OBJ mesh in the image plane.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def norm(s: str) -> str:
    s = str(s).strip().replace(" ", "_")
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.lower().strip("_")


def read_video_size(path: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    if not path:
        return None, None, None
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None, None, None
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or None
        cap.release()
        return w, h, fps
    except Exception:
        return None, None, None


def load_any_dlc(path: Path, individual: Optional[str]) -> pd.DataFrame:
    """Return long dataframe: frame, individual, bodypart, x, y, likelihood."""
    if path.suffix.lower() in {".h5", ".hdf", ".hdf5"}:
        df = pd.read_hdf(path)
    else:
        # Try DLC multi-row header first, then normal CSV.
        try:
            df = pd.read_csv(path, header=[0, 1, 2, 3], index_col=0)
            if not isinstance(df.columns, pd.MultiIndex) or df.columns.nlevels < 3:
                raise ValueError
        except Exception:
            try:
                df = pd.read_csv(path, header=[0, 1, 2], index_col=0)
                if not isinstance(df.columns, pd.MultiIndex) or df.columns.nlevels < 3:
                    raise ValueError
            except Exception:
                df = pd.read_csv(path)

    # Already long.
    cols_norm = {norm(c): c for c in df.columns}
    if {"frame", "bodypart", "x", "y"}.issubset(cols_norm):
        out = pd.DataFrame({
            "frame": df[cols_norm["frame"]].astype(int),
            "individual": df[cols_norm.get("individual", cols_norm.get("dog_id", cols_norm.get("track", "frame")))].astype(str)
                if any(k in cols_norm for k in ["individual", "dog_id", "track"]) else "animal0",
            "bodypart": df[cols_norm["bodypart"]].map(norm),
            "x": pd.to_numeric(df[cols_norm["x"]], errors="coerce"),
            "y": pd.to_numeric(df[cols_norm["y"]], errors="coerce"),
            "likelihood": pd.to_numeric(df[cols_norm.get("likelihood", cols_norm.get("p", cols_norm["x"]))], errors="coerce")
                if any(k in cols_norm for k in ["likelihood", "p"]) else 1.0,
        })
        if individual:
            out = out[out["individual"].astype(str) == individual]
        return out

    # DLC wide dataframe with MultiIndex columns.
    if not isinstance(df.columns, pd.MultiIndex):
        raise SystemExit("Could not understand DLC file format. Use DLC .h5/.csv or long CSV with frame,bodypart,x,y,likelihood.")

    records = []
    nlevels = df.columns.nlevels
    # Common layouts:
    # single animal: scorer, bodyparts, coords
    # multi animal: scorer, individuals, bodyparts, coords
    for col in df.columns:
        values = [str(v) for v in col]
        coord = norm(values[-1])
        if coord not in {"x", "y", "likelihood"}:
            continue
        if nlevels >= 4:
            ind = values[-3]
            bp = values[-2]
        else:
            ind = "animal0"
            bp = values[-2]
        if individual and str(ind) != individual:
            continue
        for frame, val in df[col].items():
            records.append((int(frame), str(ind), norm(bp), coord, val))

    tmp = pd.DataFrame(records, columns=["frame", "individual", "bodypart", "coord", "value"])
    if tmp.empty:
        raise SystemExit("No DLC keypoints found after filtering. Check --individual.")
    out = tmp.pivot_table(index=["frame", "individual", "bodypart"], columns="coord", values="value", aggfunc="first").reset_index()
    if "likelihood" not in out.columns:
        out["likelihood"] = 1.0
    return out[["frame", "individual", "bodypart", "x", "y", "likelihood"]]


def parse_renames(items: List[str]) -> Dict[str, str]:
    mapping = {}
    for item in items:
        if ":" not in item:
            raise SystemExit(f"Bad --rename '{item}'. Use old:new")
        old, new = item.split(":", 1)
        mapping[norm(old)] = norm(new)
    return mapping


def smooth_series(y: pd.Series, window: int) -> pd.Series:
    if window <= 1:
        return y
    if window % 2 == 0:
        raise SystemExit("--smooth-window must be odd")
    return y.rolling(window, center=True, min_periods=1).mean()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dlc", required=True, help="DLC .h5/.csv or long CSV")
    ap.add_argument("--out", required=True, help="Output coords_3d.csv")
    ap.add_argument("--video", default=None, help="Original video, used to read width/height/fps")
    ap.add_argument("--image-width", type=int, default=None)
    ap.add_argument("--image-height", type=int, default=None)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--individual", default=None, help="e.g. animal0; omit for first/single individual")
    ap.add_argument("--pcutoff", type=float, default=0.6)
    ap.add_argument("--keep-bodyparts", default="", help="Comma-separated target bodyparts to keep; default keeps all")
    ap.add_argument("--rename", action="append", default=[], help="Rename DLC bodypart old:new; repeatable")
    ap.add_argument("--scale", type=float, default=1.0, help="World units per video pixel")
    ap.add_argument("--depth-y", type=float, default=0.0, help="Constant pseudo-depth Y")
    ap.add_argument("--smooth-window", type=int, default=5, help="Odd moving-average window; 1 disables")
    ap.add_argument("--no-interpolate", action="store_true", help="Do not interpolate low-confidence/missing points")
    args = ap.parse_args()

    vw, vh, vfps = read_video_size(args.video)
    width = args.image_width or vw
    height = args.image_height or vh
    fps = args.fps or vfps or 30.0

    df = load_any_dlc(Path(args.dlc), args.individual)
    if df.empty:
        raise SystemExit("No DLC rows loaded.")

    # If no individual specified and multiple individuals exist, pick the first stable one.
    if args.individual is None and df["individual"].nunique() > 1:
        first = sorted(df["individual"].astype(str).unique())[0]
        print(f"Multiple individuals found; using {first}. Pass --individual to change this.")
        df = df[df["individual"].astype(str) == first]

    ren = parse_renames(args.rename)
    df["bodypart"] = df["bodypart"].map(lambda b: ren.get(norm(b), norm(b)))

    if args.keep_bodyparts.strip():
        keep = {norm(x) for x in args.keep_bodyparts.split(",") if x.strip()}
        df = df[df["bodypart"].isin(keep)]

    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["likelihood"] = pd.to_numeric(df["likelihood"], errors="coerce").fillna(0.0)
    df.loc[df["likelihood"] < args.pcutoff, ["x", "y"]] = np.nan

    if height is None:
        ymax = float(np.nanmax(df["y"].to_numpy()))
        height = int(np.ceil(ymax))
        print(f"No video/image height given; using max y as height={height}.")

    out_rows = []
    for bp, g in df.groupby("bodypart", sort=True):
        g = g.sort_values("frame").copy()
        all_frames = pd.DataFrame({"frame": np.arange(int(df["frame"].min()), int(df["frame"].max()) + 1)})
        g = all_frames.merge(g[["frame", "x", "y", "likelihood"]], on="frame", how="left")
        if not args.no_interpolate:
            g["x"] = g["x"].interpolate(limit_direction="both")
            g["y"] = g["y"].interpolate(limit_direction="both")
        g["x"] = smooth_series(g["x"], args.smooth_window)
        g["y"] = smooth_series(g["y"], args.smooth_window)
        for rr in g.itertuples(index=False):
            if not np.isfinite(rr.x) or not np.isfinite(rr.y):
                continue
            frame = int(rr.frame)
            xw = float(rr.x) * args.scale
            yw = float(args.depth_y)
            zw = (float(height) - float(rr.y)) * args.scale
            out_rows.append({
                "frame": frame,
                "time": frame / float(fps),
                "dog_id": 0,
                "behavior": 0,
                "node": bp,
                "x": xw,
                "y": yw,
                "z": zw,
            })

    out = pd.DataFrame(out_rows)
    out = out.sort_values(["frame", "dog_id", "node"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    meta = {"width": width, "height": height, "fps": fps, "scale": args.scale, "pseudo_3d": "X=image_x, Y=constant, Z=image_height-image_y"}
    Path(str(args.out) + ".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {args.out} with {len(out)} rows, {out['frame'].nunique()} frames, {out['node'].nunique()} nodes")


if __name__ == "__main__":
    main()
