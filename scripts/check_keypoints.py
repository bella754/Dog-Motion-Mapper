"""
Displays detected animals and available keypoints from a DeepLabCut .h5 file.
"""
import argparse
from pathlib import Path
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Show scorer, individuals and bodyparts from a DLC/SuperAnimal .h5 file.")
    parser.add_argument("path", help="Pfad zur .h5 Datei")
    parser.add_argument("--individuals", nargs="+", default=["animal0", "animal1", "animal2", "animal3", "animal4"])
    return parser.parse_args()

def main():
    args = parse_args()
    path = Path(args.path)

    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    df = pd.read_hdf(path)

    # individuals = args.individuals
    individuals = sorted(df.columns.get_level_values("individuals").unique())
    bodyparts = sorted(df.columns.get_level_values("bodyparts").unique())

    print("individuals:", individuals)
    print("number of individuals:", len(individuals))
    print("number of bodyparts:", len(bodyparts))
    print("bodyparts:")
    for bp in bodyparts:
        print(" ", bp)

if __name__ == "__main__":
    main()
