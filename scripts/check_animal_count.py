"""
Prüft pro tier, wie oft genug keypoints sichtbar sind 
- likelihood: wie sicher soll sich das modell bei dem keypoint sein?
- min-visible-keypoints: wie viele keypoints sollen mind. sichtbar sein, damit count +=1?

Basically: 
    For each animal: In how many frames were #<min-visible-keypoints> with likelihood bigger than <likelihood-thershold> detectd? 
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Count visible DLC/SuperAnimal keypoints per animal.")
    parser.add_argument("path", help="Pfad zur .h5 Datei")
    parser.add_argument("--likelihood-threshold", type=float, default=0.8)
    parser.add_argument("--min-visible-keypoints", type=int, default=8)
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
    bodyparts = sorted(df.columns.get_level_values("bodyparts").unique())

    for animal in individuals:
        likelihoods = df.loc[:, (scorer, animal, bodyparts, "likelihood")]
        visible_per_frame = (likelihoods > args.likelihood_threshold).sum(axis=1)
        frames_visible = (visible_per_frame >= args.min_visible_keypoints).sum()

        print(
            animal,
            "visible frames:",
            frames_visible,
            "/",
            len(df),
            "avg visible keypoints:",
            round(visible_per_frame.mean(), 2),
        )

if __name__ == "__main__":
    main()
