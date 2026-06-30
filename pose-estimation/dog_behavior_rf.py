"""
Train, validate and test a Random Forest dog-behaviour classifier from exported DLC/SuperAnimal CSV keypoints.

Expected dataset layout, for example:

pose-estimation/
  train/
    sitting-1.csv
    resting-1.csv
    walking-1.csv
  val/
    sitting-val.csv
    resting-val.csv
    walking-val.csv
  test/
    sitting-test-1.csv
    sitting-test-2.csv
    resting-test-1.csv
    walking-test-1.csv

Expected CSV format:
frame, animal, bodypart, x, y, likelihood

The model uses relative pose/motion features, not absolute image movement:
- every frame is centered on back_middle if available
- distances/speeds are normalized by body length if available
- windows of e.g. 1 second are classified, then video labels are majority-voted
"""

from __future__ import annotations

import argparse
import json
import warnings
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEFAULT_LABELS = ("sitting", "resting", "walking")
LABEL_ALIASES = {
    "sit": "sitting",
    "sitting": "sitting",
    "rest": "resting",
    "resting": "resting",
    "lying": "resting",
    "lie": "resting",
    "laying": "resting",
    "walk": "walking",
    "walking": "walking",
}

CENTER_CANDIDATES = [
    "back_middle",
    "body_middle",
    "body_middle_left",
    "body_middle_right",
    "back_base",
]

SCALE_PAIRS = [
    ("back_base", "back_end"),
    ("nose", "back_end"),
    ("nose", "back_base"),
    ("body_middle_left", "body_middle_right"),
]

IMPORTANT_KEYPOINTS = [
    "nose",
    "back_base",
    "back_middle",
    "back_end",
    "belly_bottom",
    "body_middle_left",
    "body_middle_right",
    "front_left_paw",
    "front_right_paw",
    "back_left_paw",
    "back_right_paw",
    "front_left_knee",
    "front_right_knee",
    "back_left_knee",
    "back_right_knee",
]

PAIR_FEATURES = [
    ("nose", "back_base"),
    ("nose", "back_middle"),
    ("nose", "back_end"),
    ("back_base", "back_middle"),
    ("back_middle", "back_end"),
    ("back_base", "back_end"),
    ("back_middle", "front_left_paw"),
    ("back_middle", "front_right_paw"),
    ("back_middle", "back_left_paw"),
    ("back_middle", "back_right_paw"),
    ("front_left_paw", "front_right_paw"),
    ("back_left_paw", "back_right_paw"),
    ("front_left_paw", "back_left_paw"),
    ("front_right_paw", "back_right_paw"),
    ("front_left_paw", "back_right_paw"),
    ("front_right_paw", "back_left_paw"),
]

PAW_KEYPOINTS = [
    "front_left_paw",
    "front_right_paw",
    "back_left_paw",
    "back_right_paw",
]


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------

def sanitize_bodypart_name(name: object) -> str:
    """Normalize bodypart names from DLC/Blender naming variants."""
    s = str(name).strip()
    s = s.replace(" ", "_").replace("-", "_")
    s = s.lower()
    if s.startswith("kp_"):
        s = s[3:]
    return s


def infer_split(path: Path) -> Optional[str]:
    parts = [p.lower() for p in path.parts]
    for split in ("train", "val", "test"):
        if split in parts:
            return split
    return None


def infer_label(path: Path, labels: Iterable[str]) -> Optional[str]:
    text = " ".join([path.stem.lower(), *[p.lower() for p in path.parts]])
    # Prefer explicit aliases first.
    for key, canonical in LABEL_ALIASES.items():
        if canonical in labels and key in text:
            return canonical
    # Then exact labels.
    for label in labels:
        if label.lower() in text:
            return label
    return None


def safe_nan_stat(values: np.ndarray, stat: str) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0 or np.all(np.isnan(values)):
        return np.nan
    if stat == "mean":
        return float(np.nanmean(values))
    if stat == "std":
        return float(np.nanstd(values))
    if stat == "min":
        return float(np.nanmin(values))
    if stat == "max":
        return float(np.nanmax(values))
    if stat == "range":
        return float(np.nanmax(values) - np.nanmin(values))
    if stat == "median":
        return float(np.nanmedian(values))
    raise ValueError(f"Unknown stat: {stat}")

# pythagoras
def distance_xy(ax: np.ndarray, ay: np.ndarray, bx: np.ndarray, by: np.ndarray) -> np.ndarray:
    return np.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# ---------------------------------------------------------------------
# Loading keypoint CSV files
# ---------------------------------------------------------------------

def load_keypoints(path: Path, animal: Optional[str] = None) -> pd.DataFrame:
    """
    Load an exported keypoint CSV and return a flat dataframe with columns like:
    back_middle_x, back_middle_y, back_middle_likelihood, ...

    Expected CSV columns:
    frame, animal, bodypart, x, y, likelihood
    """
    path = Path(path)

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, got: {path}")

    df = pd.read_csv(path)
    return long_to_flat(df, animal=animal)


def long_to_flat(df: pd.DataFrame, animal: Optional[str] = None) -> pd.DataFrame:
    colmap = {c.lower().strip(): c for c in df.columns}

    required = {"frame", "bodypart", "x", "y", "likelihood"}
    missing = required - set(colmap.keys())
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    frame_col = colmap["frame"]
    bodypart_col = colmap["bodypart"]
    x_col = colmap["x"]
    y_col = colmap["y"]
    likelihood_col = colmap["likelihood"]
    animal_col = colmap.get("animal")

    data = df.copy()

    if animal is not None and animal_col is not None:
        data = data[data[animal_col].astype(str) == str(animal)]

    data["_bodypart"] = data[bodypart_col].map(sanitize_bodypart_name)
    data["_frame"] = pd.to_numeric(data[frame_col], errors="coerce").astype("Int64")
    data = data.dropna(subset=["_frame", "_bodypart"])

    flat_parts = []

    for value_col, suffix in [
        (x_col, "x"),
        (y_col, "y"),
        (likelihood_col, "likelihood"),
    ]:
        tmp = data.pivot_table(
            index="_frame",
            columns="_bodypart",
            values=value_col,
            aggfunc="first",
        )
        tmp = tmp.add_suffix(f"_{suffix}")
        flat_parts.append(tmp)

    flat = pd.concat(flat_parts, axis=1).sort_index()
    flat.index.name = "frame"

    return flat

# ---------------------------------------------------------------------
# Preprocessing and feature extraction
# ---------------------------------------------------------------------

def available_bodyparts(flat: pd.DataFrame) -> List[str]:
    bps = sorted({c[:-2] for c in flat.columns if c.endswith("_x") and f"{c[:-2]}_y" in flat.columns})
    return bps


def apply_likelihood_filter(flat: pd.DataFrame, min_likelihood: float) -> pd.DataFrame:
    out = flat.copy()
    for bp in available_bodyparts(out):
        like_col = f"{bp}_likelihood"
        if like_col not in out.columns:
            continue
        bad = pd.to_numeric(out[like_col], errors="coerce") < min_likelihood
        out.loc[bad, f"{bp}_x"] = np.nan
        out.loc[bad, f"{bp}_y"] = np.nan
    return out


def interpolate_keypoints(flat: pd.DataFrame) -> pd.DataFrame:
    out = flat.copy()
    xy_cols = [c for c in out.columns if c.endswith("_x") or c.endswith("_y")]
    out[xy_cols] = out[xy_cols].apply(pd.to_numeric, errors="coerce")
    # Fill short and edge gaps; for very noisy data, you can make this stricter.
    out[xy_cols] = out[xy_cols].interpolate(method="linear", limit_direction="both")
    out[xy_cols] = out[xy_cols].bfill().ffill()
    return out


def get_xy(flat: pd.DataFrame, bp: str) -> Tuple[np.ndarray, np.ndarray]:
    x_col, y_col = f"{bp}_x", f"{bp}_y"
    n = len(flat)
    if x_col not in flat.columns or y_col not in flat.columns:
        return np.full(n, np.nan), np.full(n, np.nan)
    return flat[x_col].to_numpy(dtype=float), flat[y_col].to_numpy(dtype=float)


def compute_center(flat: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, str]:
    bps = available_bodyparts(flat)
    for bp in CENTER_CANDIDATES:
        if bp in bps:
            x, y = get_xy(flat, bp)
            if not np.all(np.isnan(x)) and not np.all(np.isnan(y)):
                return x, y, bp

    # Fallback: median of all available keypoints per frame.
    x_cols = [f"{bp}_x" for bp in bps if f"{bp}_x" in flat.columns]
    y_cols = [f"{bp}_y" for bp in bps if f"{bp}_y" in flat.columns]
    cx = flat[x_cols].median(axis=1).to_numpy(dtype=float) if x_cols else np.zeros(len(flat))
    cy = flat[y_cols].median(axis=1).to_numpy(dtype=float) if y_cols else np.zeros(len(flat))
    return cx, cy, "median_all_keypoints"


def compute_scale(flat: pd.DataFrame) -> Tuple[np.ndarray, str]:
    n = len(flat)
    for a, b in SCALE_PAIRS:
        ax, ay = get_xy(flat, a)
        bx, by = get_xy(flat, b)
        dist = distance_xy(ax, ay, bx, by)
        median = np.nanmedian(dist)
        if np.isfinite(median) and median > 1e-6:
            dist = np.where(np.isfinite(dist) & (dist > 1e-6), dist, median)
            return dist, f"distance_{a}_to_{b}"

    # Fallback: bounding-box diagonal per frame.
    bps = available_bodyparts(flat)
    x_cols = [f"{bp}_x" for bp in bps if f"{bp}_x" in flat.columns]
    y_cols = [f"{bp}_y" for bp in bps if f"{bp}_y" in flat.columns]
    if x_cols and y_cols:
        width = flat[x_cols].max(axis=1) - flat[x_cols].min(axis=1)
        height = flat[y_cols].max(axis=1) - flat[y_cols].min(axis=1)
        diag = np.sqrt(width.to_numpy(dtype=float) ** 2 + height.to_numpy(dtype=float) ** 2)
        median = np.nanmedian(diag)
        if np.isfinite(median) and median > 1e-6:
            diag = np.where(np.isfinite(diag) & (diag > 1e-6), diag, median)
            return diag, "bbox_diagonal"

    return np.ones(n), "constant_1"


def build_relative_table(flat: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Create normalized, body-centered coordinate table."""
    cx, cy, center_name = compute_center(flat)
    scale, scale_name = compute_scale(flat)
    scale = np.where(np.isfinite(scale) & (scale > 1e-6), scale, np.nanmedian(scale[np.isfinite(scale)]) if np.any(np.isfinite(scale)) else 1.0)

    rel = pd.DataFrame(index=flat.index)
    bps = available_bodyparts(flat)
    for bp in bps:
        x, y = get_xy(flat, bp)
        rel[f"{bp}_rx"] = (x - cx) / scale
        rel[f"{bp}_ry"] = (y - cy) / scale
        like_col = f"{bp}_likelihood"
        if like_col in flat.columns:
            rel[f"{bp}_likelihood"] = pd.to_numeric(flat[like_col], errors="coerce")

    return rel, {"center": center_name, "scale": scale_name}


def add_stats(features: Dict[str, float], prefix: str, values: np.ndarray, stats: Iterable[str] = ("mean", "std", "min", "max", "range")) -> None:
    for stat in stats:
        features[f"{prefix}_{stat}"] = safe_nan_stat(values, stat)


def extract_window_features(
    rel: pd.DataFrame,
    fps: float,
    window_sec: float,
    stride_sec: float,
    video_id: str,
    split: str,
    label: str,
) -> List[Dict[str, object]]:
    window_frames = max(2, int(round(window_sec * fps)))
    stride_frames = max(1, int(round(stride_sec * fps)))
    n = len(rel)

    if n < window_frames:
        # For very short clips, use one whole-video window.
        starts = [0]
        window_frames = n
    else:
        starts = list(range(0, n - window_frames + 1, stride_frames))

    bodyparts = sorted({c[:-3] for c in rel.columns if c.endswith("_rx") and f"{c[:-3]}_ry" in rel.columns})
    selected_bps = [bp for bp in IMPORTANT_KEYPOINTS if bp in bodyparts]
    # Add any remaining bodyparts after the important ones.
    selected_bps += [bp for bp in bodyparts if bp not in selected_bps]

    rows: List[Dict[str, object]] = []
    for start in starts:
        end = min(start + window_frames, n)
        w = rel.iloc[start:end]
        features: Dict[str, object] = {
            "video_id": video_id,
            "split": split,
            "label": label,
            "window_start_frame": int(start),
            "window_end_frame": int(end - 1),
            "window_start_sec": float(start / fps),
            "window_end_sec": float((end - 1) / fps),
            "n_frames": int(end - start),
        }

        # Per-keypoint relative coordinate and speed features.
        all_speeds = []
        paw_speeds = []
        for bp in selected_bps:
            rx = w[f"{bp}_rx"].to_numpy(dtype=float)
            ry = w[f"{bp}_ry"].to_numpy(dtype=float)
            add_stats(features, f"{bp}_rx", rx)
            add_stats(features, f"{bp}_ry", ry)

            if len(rx) >= 2:
                speed = np.sqrt(np.diff(rx) ** 2 + np.diff(ry) ** 2) * fps
            else:
                speed = np.array([np.nan])
            add_stats(features, f"{bp}_rel_speed", speed, stats=("mean", "std", "max"))
            all_speeds.append(speed)
            if bp in PAW_KEYPOINTS:
                paw_speeds.append(speed)

            like_col = f"{bp}_likelihood"
            if like_col in w.columns:
                likes = w[like_col].to_numpy(dtype=float)
                features[f"{bp}_low_likelihood_fraction"] = float(np.mean(likes < 0.8)) if len(likes) else np.nan
                features[f"{bp}_likelihood_mean"] = safe_nan_stat(likes, "mean")

        if all_speeds:
            concat = np.concatenate(all_speeds)
            add_stats(features, "all_keypoints_rel_speed", concat, stats=("mean", "std", "max"))
        if paw_speeds:
            concat = np.concatenate(paw_speeds)
            add_stats(features, "all_paws_rel_speed", concat, stats=("mean", "std", "max"))

        # Pairwise distance features in normalized relative coordinates.
        for a, b in PAIR_FEATURES:
            if a in bodyparts and b in bodyparts:
                ax = w[f"{a}_rx"].to_numpy(dtype=float)
                ay = w[f"{a}_ry"].to_numpy(dtype=float)
                bx = w[f"{b}_rx"].to_numpy(dtype=float)
                by = w[f"{b}_ry"].to_numpy(dtype=float)
                dist = distance_xy(ax, ay, bx, by)
                add_stats(features, f"dist_{a}_to_{b}", dist)

        # Bounding box features in normalized coordinates.
        rx_cols = [f"{bp}_rx" for bp in bodyparts if f"{bp}_rx" in w.columns]
        ry_cols = [f"{bp}_ry" for bp in bodyparts if f"{bp}_ry" in w.columns]
        if rx_cols and ry_cols:
            widths = w[rx_cols].max(axis=1) - w[rx_cols].min(axis=1)
            heights = w[ry_cols].max(axis=1) - w[ry_cols].min(axis=1)
            ratio = widths / heights.replace(0, np.nan)
            area = widths * heights
            add_stats(features, "bbox_width_norm", widths.to_numpy(dtype=float), stats=("mean", "std", "min", "max"))
            add_stats(features, "bbox_height_norm", heights.to_numpy(dtype=float), stats=("mean", "std", "min", "max"))
            add_stats(features, "bbox_ratio_norm", ratio.to_numpy(dtype=float), stats=("mean", "std", "min", "max"))
            add_stats(features, "bbox_area_norm", area.to_numpy(dtype=float), stats=("mean", "std", "min", "max"))

        rows.append(features)

    return rows


# ---------------------------------------------------------------------
# Dataset and model training
# ---------------------------------------------------------------------

def discover_keypoint_files(data_root: Path, labels: Iterable[str]) -> pd.DataFrame:
    files = []

    for path in data_root.rglob("*.csv"):
        # Avoid reading our own output files.
        lowered = str(path).lower()
        if any(part in lowered for part in [
            "rf_outputs",
            "features_all",
            "window_predictions",
            "video_predictions",
            "feature_importance",
        ]):
            continue

        split = infer_split(path)
        label = infer_label(path, labels)

        if split is None or label is None:
            continue

        files.append({
            "path": str(path),
            "split": split,
            "label": label,
            "video_id": path.stem,
        })

    return pd.DataFrame(files)

def build_feature_dataset(
    data_root: Path,
    fps: float,
    window_sec: float,
    stride_sec: float,
    min_likelihood: float,
    animal: Optional[str],
    labels: Iterable[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    meta = discover_keypoint_files(data_root, labels=labels)
    if meta.empty:
        raise RuntimeError(
            f"No keypoint CSV files found below {data_root}.\n"
            "You need exported DLC/SuperAnimal keypoint CSV files first, not .mp4 videos or .h5 files.\n"
            "Put the CSV files into train/ val/ test/ folders and include the class name in the filename, "
            "e.g. train/walking-1.csv, val/sitting-val.csv."
        )

    all_rows: List[Dict[str, object]] = []
    file_infos: List[Dict[str, object]] = []

    for _, item in meta.iterrows():
        path = Path(item["path"])
        split = str(item["split"])
        label = str(item["label"])
        video_id = str(item["video_id"])
        print(f"Loading {split:5s} {label:8s} {path}")

        flat = load_keypoints(path, animal=animal)
        flat = apply_likelihood_filter(flat, min_likelihood=min_likelihood)
        flat = interpolate_keypoints(flat)
        rel, info = build_relative_table(flat)
        rows = extract_window_features(
            rel=rel,
            fps=fps,
            window_sec=window_sec,
            stride_sec=stride_sec,
            video_id=video_id,
            split=split,
            label=label,
        )
        all_rows.extend(rows)
        file_infos.append({
            "path": str(path),
            "split": split,
            "label": label,
            "video_id": video_id,
            "n_frames": len(flat),
            "n_windows": len(rows),
            "center_used": info["center"],
            "scale_used": info["scale"],
            "bodyparts": ",".join(available_bodyparts(flat)),
        })

    features = pd.DataFrame(all_rows)
    file_info_df = pd.DataFrame(file_infos)
    return features, file_info_df


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    ignore = {
        "video_id",
        "split",
        "label",
        "window_start_frame",
        "window_end_frame",
        "window_start_sec",
        "window_end_sec",
        "n_frames",
    }
    cols = [c for c in df.columns if c not in ignore]
    numeric_cols = []
    for c in cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            numeric_cols.append(c)
    return numeric_cols


def make_video_predictions(window_df: pd.DataFrame, pred_col: str = "prediction") -> pd.DataFrame:
    rows = []
    for video_id, group in window_df.groupby("video_id"):
        labels = group[pred_col].astype(str).tolist()
        majority = Counter(labels).most_common(1)[0][0]
        true_label = group["label"].iloc[0]
        split = group["split"].iloc[0]
        counts = dict(Counter(labels))
        rows.append({
            "video_id": video_id,
            "split": split,
            "true_label": true_label,
            "predicted_label": majority,
            "correct": bool(majority == true_label),
            "n_windows": len(group),
            "prediction_counts": json.dumps(counts, sort_keys=True),
        })
    return pd.DataFrame(rows).sort_values(["split", "video_id"])


def evaluate_split(model: Pipeline, df: pd.DataFrame, feature_cols: List[str], split_name: str, output_dir: Path) -> None:
    if df.empty:
        print(f"\nNo data for split {split_name!r}; skipping.")
        return

    X = df[feature_cols]
    y = df["label"]
    pred = model.predict(X)

    print(f"\n=== Window-level evaluation: {split_name} ===")
    print(f"Accuracy: {accuracy_score(y, pred):.3f}")
    print(classification_report(y, pred, zero_division=0))
    print("Confusion matrix labels:", list(model.named_steps["rf"].classes_))
    print(confusion_matrix(y, pred, labels=model.named_steps["rf"].classes_))

    out = df[["video_id", "split", "label", "window_start_sec", "window_end_sec"]].copy()
    out["prediction"] = pred
    if hasattr(model.named_steps["rf"], "predict_proba"):
        proba = model.predict_proba(X)
        for i, cls in enumerate(model.named_steps["rf"].classes_):
            out[f"proba_{cls}"] = proba[:, i]
    out.to_csv(output_dir / f"window_predictions_{split_name}.csv", index=False)

    video_pred = make_video_predictions(out, pred_col="prediction")
    print(f"\n=== Video-level majority vote: {split_name} ===")
    if not video_pred.empty:
        print(video_pred[["video_id", "true_label", "predicted_label", "correct", "n_windows", "prediction_counts"]].to_string(index=False))
        video_acc = float(video_pred["correct"].mean())
        print(f"Video-level accuracy: {video_acc:.3f}")
    video_pred.to_csv(output_dir / f"video_predictions_{split_name}.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train/test Random Forest dog behaviour classifier from keypoints.")
    parser.add_argument("--data-root", type=Path, required=True, help="Root folder containing train/ val/ test/ keypoint CSV/H5 files.")
    parser.add_argument("--output-dir", type=Path, default=Path("rf_outputs"), help="Where outputs/model are written.")
    parser.add_argument("--fps", type=float, default=30.0, help="FPS used for windowing and speed features. Use your clip FPS or normalize clips first.")
    parser.add_argument("--window-sec", type=float, default=1.0, help="Window length in seconds.")
    parser.add_argument("--stride-sec", type=float, default=0.5, help="Sliding-window stride in seconds.")
    parser.add_argument("--min-likelihood", type=float, default=0.6, help="Keypoints below this DLC likelihood are treated as missing.")
    parser.add_argument("--animal", type=str, default=None, help="For multi-animal DLC files, choose e.g. animal0. Default: first animal.")
    parser.add_argument("--labels", nargs="+", default=list(DEFAULT_LABELS), help="Class labels to use/infer from filenames.")
    parser.add_argument("--n-estimators", type=int, default=500, help="Number of trees in the Random Forest.")
    parser.add_argument("--max-depth", type=int, default=None, help="Optional max_depth for Random Forest.")
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    features, file_info = build_feature_dataset(
        data_root=args.data_root,
        fps=args.fps,
        window_sec=args.window_sec,
        stride_sec=args.stride_sec,
        min_likelihood=args.min_likelihood,
        animal=args.animal,
        labels=args.labels,
    )

    features.to_csv(args.output_dir / "features_all.csv", index=False)
    file_info.to_csv(args.output_dir / "file_info.csv", index=False)

    print("\n=== Loaded files ===")
    print(file_info[["split", "label", "video_id", "n_frames", "n_windows", "center_used", "scale_used"]].to_string(index=False))

    print("\n=== Window counts ===")
    print(features.groupby(["split", "label"]).size().rename("n_windows").to_string())

    feature_cols = get_feature_columns(features)
    if not feature_cols:
        raise RuntimeError("No numeric feature columns extracted.")

    train_df = features[features["split"] == "train"].copy()
    val_df = features[features["split"] == "val"].copy()
    test_df = features[features["split"] == "test"].copy()

    if train_df.empty:
        raise RuntimeError("No training data found. Check train/ folder and filenames.")

    X_train = train_df[feature_cols]
    y_train = train_df["label"]

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            class_weight="balanced",
            random_state=args.random_state,
            n_jobs=-1,
        )),
    ])

    print("\nTraining Random Forest...")
    model.fit(X_train, y_train)

    # Save model plus feature columns/config, so inference later uses the same columns.
    bundle = {
        "model": model,
        "feature_cols": feature_cols,
        "config": vars(args),
    }
    joblib.dump(bundle, args.output_dir / "dog_behavior_random_forest.joblib")
    print(f"Saved model to: {args.output_dir / 'dog_behavior_random_forest.joblib'}")

    # Feature importance.
    importances = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.named_steps["rf"].feature_importances_,
    }).sort_values("importance", ascending=False)
    importances.to_csv(args.output_dir / "feature_importance.csv", index=False)
    print("\n=== Top 20 feature importances ===")
    print(importances.head(20).to_string(index=False))

    evaluate_split(model, train_df, feature_cols, "train", args.output_dir)
    evaluate_split(model, val_df, feature_cols, "val", args.output_dir)
    evaluate_split(model, test_df, feature_cols, "test", args.output_dir)

    print("\nDone. Important output files:")
    print(f"  {args.output_dir / 'features_all.csv'}")
    print(f"  {args.output_dir / 'file_info.csv'}")
    print(f"  {args.output_dir / 'feature_importance.csv'}")
    print(f"  {args.output_dir / 'dog_behavior_random_forest.joblib'}")
    print(f"  {args.output_dir / 'window_predictions_test.csv'}")
    print(f"  {args.output_dir / 'video_predictions_test.csv'}")


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        main()
