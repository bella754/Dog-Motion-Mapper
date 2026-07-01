"""
Reads a DeepLabCut .h5 file and prints a brief summary to the terminal.
"""
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Pfad zur .h5 Datei")

    args = parser.parse_args()

    df = pd.read_hdf(args.path)

    print(df.shape)
    print(df.head())
    print(df.columns)

if __name__ == "__main__":
    main()