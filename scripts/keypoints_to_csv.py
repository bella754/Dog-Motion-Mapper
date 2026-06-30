"""
Extract keypoints from .h5 file for one animal and put them into a csv
"""

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_h5", help="DLC .h5 Datei")
    parser.add_argument("output_csv", help="Output CSV Datei")
    parser.add_argument("--animal", default="animal0")
    parser.add_argument("--likelihood-threshold", type=float, default=0.8)
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input_h5)
    output_path = Path(args.output_csv)

    if not input_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {input_path}")

    df = pd.read_hdf(input_path)

    scorer = df.columns.get_level_values("scorer")[0]
    bodyparts = sorted(df.columns.get_level_values("bodyparts").unique())

    rows = []

    for frame_idx in range(len(df)):
        for bp in bodyparts:
            x = df.loc[frame_idx, (scorer, args.animal, bp, "x")]
            y = df.loc[frame_idx, (scorer, args.animal, bp, "y")]
            likelihood = df.loc[frame_idx, (scorer, args.animal, bp, "likelihood")]

            if likelihood < args.likelihood_threshold:
                continue

            rows.append(
                {
                    "frame": frame_idx,
                    "animal": args.animal,
                    "bodypart": bp,
                    "x": x,
                    "y": y,
                    "likelihood": likelihood,
                }
            )

    out_df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")
    print(f"Rows: {len(out_df)}")
    print(f"Frames: {out_df['frame'].nunique() if len(out_df) > 0 else 0}")
    print(f"Bodyparts: {out_df['bodypart'].nunique() if len(out_df) > 0 else 0}")


if __name__ == "__main__":
    main()