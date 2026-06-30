"""
Convert all DLC/SuperAnimal .h5 files in a folder to simple keypoint CSV files.

Each output CSV contains:
frame, animal, bodypart, x, y, likelihood

Recommended for Random Forest preprocessing:
use --likelihood-threshold 0.0 to keep all keypoints and filter later.
"""

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert all DLC/SuperAnimal .h5 files in a folder to keypoint CSV files."
    )
    parser.add_argument("input_dir", help="Ordner mit .h5 Dateien")
    parser.add_argument("output_dir", help="Ordner für die exportierten CSV Dateien")
    parser.add_argument("--animal", default="animal0", help="Welches Tier exportiert werden soll")
    parser.add_argument(
        "--likelihood-threshold",
        type=float,
        default=0.0,
        help="Keypoints unter diesem Likelihood-Wert werden übersprungen",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Existierende CSV Dateien überschreiben",
    )
    return parser.parse_args()


def export_h5_to_csv(input_path, output_path, animal, likelihood_threshold):
    df = pd.read_hdf(input_path)

    scorer = df.columns.get_level_values("scorer")[0]
    bodyparts = sorted(df.columns.get_level_values("bodyparts").unique())

    available_animals = sorted(df.columns.get_level_values("individuals").unique())
    if animal not in available_animals:
        raise ValueError(
            f"{animal} nicht in {input_path.name} gefunden. "
            f"Verfügbar: {available_animals}"
        )

    rows = []

    for frame_idx in range(len(df)):
        for bp in bodyparts:
            x = df.loc[frame_idx, (scorer, animal, bp, "x")]
            y = df.loc[frame_idx, (scorer, animal, bp, "y")]
            likelihood = df.loc[frame_idx, (scorer, animal, bp, "likelihood")]

            if likelihood < likelihood_threshold:
                continue

            rows.append(
                {
                    "frame": frame_idx,
                    "animal": animal,
                    "bodypart": bp,
                    "x": x,
                    "y": y,
                    "likelihood": likelihood,
                }
            )

    out_df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_path, index=False)

    return len(out_df), out_df["frame"].nunique() if len(out_df) > 0 else 0


def main():
    args = parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input-Ordner nicht gefunden: {input_dir}")

    h5_files = sorted(input_dir.rglob("*.h5"))

    if not h5_files:
        raise FileNotFoundError(f"Keine .h5 Dateien gefunden in: {input_dir}")

    print(f"Gefundene .h5 Dateien: {len(h5_files)}")
    print(f"Animal: {args.animal}")
    print(f"Likelihood threshold: {args.likelihood_threshold}")
    print("--------------------------------------------------")

    converted = 0
    skipped = 0
    failed = 0

    for h5_path in h5_files:
        relative_path = h5_path.relative_to(input_dir)
        csv_path = output_dir / relative_path.with_suffix(".csv")

        if csv_path.exists() and not args.overwrite:
            print(f"Skip, existiert schon: {csv_path}")
            skipped += 1
            continue

        try:
            rows, frames = export_h5_to_csv(
                input_path=h5_path,
                output_path=csv_path,
                animal=args.animal,
                likelihood_threshold=args.likelihood_threshold,
            )

            print(f"Saved: {csv_path}")
            print(f"  Rows: {rows}")
            print(f"  Frames: {frames}")
            converted += 1

        except Exception as exc:
            print(f"Fehler bei {h5_path}: {exc}")
            failed += 1

    print("--------------------------------------------------")
    print("Fertig.")
    print(f"Konvertiert: {converted}")
    print(f"Übersprungen: {skipped}")
    print(f"Fehler: {failed}")


if __name__ == "__main__":
    main()