"""
Checks DLC tracks for large jumps in the estimated animal center.

For each detected animal, only keypoints with sufficient likelihood are used.
From these keypoints, the center is calculated for each frame, and then
a check is performed to see if this center jumps an unusually large distance between two frames.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Check center jumps per detected animal in a DLC/SuperAnimal .h5 file.")
    parser.add_argument("path", help="Pfad zur .h5 Datei")
    parser.add_argument("--likelihood-threshold", type=float, default=0.8)
    parser.add_argument("--min-valid-keypoints", type=int, default=8)
    parser.add_argument("--jump-threshold", type=float, default=100.0, help="Schwellwert für große Sprünge in Pixeln")
    parser.add_argument("--individuals", nargs="+", default=["animal0", "animal1", "animal2", "animal3", "animal4"])
    return parser.parse_args()

def main():
    args = parse_args()
    path = Path(args.path)

    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    df = pd.read_hdf(path)

    scorer = df.columns.get_level_values("scorer")[0]
    #individuals = args.individuals
    individuals = sorted(df.columns.get_level_values("individuals").unique())
    bodyparts = list(df.columns.get_level_values("bodyparts").unique())

    for animal in individuals:
        xs = df.loc[:, (scorer, animal, bodyparts, "x")]
        ys = df.loc[:, (scorer, animal, bodyparts, "y")]
        ls = df.loc[:, (scorer, animal, bodyparts, "likelihood")]

        x_arr = xs.to_numpy(dtype=float)
        y_arr = ys.to_numpy(dtype=float)
        l_arr = ls.to_numpy(dtype=float)

        valid = l_arr > args.likelihood_threshold
        valid_count = np.sum(valid, axis=1)

        x_masked = np.where(valid, x_arr, np.nan)
        y_masked = np.where(valid, y_arr, np.nan)

        x_center = np.full(len(df), np.nan)
        y_center = np.full(len(df), np.nan)

        good_frames = valid_count >= args.min_valid_keypoints
        x_center[good_frames] = np.nanmedian(x_masked[good_frames], axis=1)
        y_center[good_frames] = np.nanmedian(y_masked[good_frames], axis=1)

        jumps = np.sqrt(np.diff(x_center) ** 2 + np.diff(y_center) ** 2)
        big_jumps = np.where(jumps > args.jump_threshold)[0] + 1

        print("\n", animal)
        print("valid center frames:", np.sum(~np.isnan(x_center)))
        print("max jump:", np.nanmax(jumps) if np.any(~np.isnan(jumps)) else np.nan)
        print(f"big jumps >{args.jump_threshold:g}px:", len(big_jumps))
        if len(big_jumps) > 0:
            print("jump frames:", list(big_jumps[:10]))

if __name__ == "__main__":
    main()
