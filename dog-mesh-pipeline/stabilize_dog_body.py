import argparse
import math
import numpy as np
import pandas as pd


BODY_NODES = ["back_base", "back_middle", "back_end", "nose"]


def rot2d(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return np.array([[c, -s], [s, c]], dtype=float)


def get_point(frame_df, node):
    row = frame_df[frame_df["node"] == node]
    if row.empty:
        return None
    r = row.iloc[0]
    return np.array([float(r["x"]), float(r["z"])], dtype=float)


def set_point(df, frame, node, xz):
    mask = (df["frame"] == frame) & (df["node"] == node)
    df.loc[mask, "x"] = xz[0]
    df.loc[mask, "z"] = xz[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-csv", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--ref-frame", type=int, default=70)
    parser.add_argument("--min-body-len-factor", type=float, default=0.65)
    args = parser.parse_args()

    df = pd.read_csv(args.in_csv)

    if "mouse_id" not in df.columns and "dog_id" in df.columns:
        # Render-Script braucht es nicht zwingend, aber sauberer ist mouse_id.
        df = df.rename(columns={"dog_id": "mouse_id"})

    ref_df = df[df["frame"] == args.ref_frame]

    ref_base = get_point(ref_df, "back_base")
    ref_end = get_point(ref_df, "back_end")

    if ref_base is None or ref_end is None:
        raise RuntimeError("Reference frame does not contain back_base/back_end.")

    ref_center = 0.5 * (ref_base + ref_end)
    ref_vec = ref_end - ref_base
    ref_len = np.linalg.norm(ref_vec)

    if ref_len < 1e-6:
        raise RuntimeError("Reference body length is too small.")

    ref_angle = math.atan2(ref_vec[1], ref_vec[0])

    # Speichere Referenz-Offsets für alle Body-Nodes relativ zum Körperzentrum.
    ref_offsets = {}
    for node in BODY_NODES:
        p = get_point(ref_df, node)
        if p is not None:
            ref_offsets[node] = p - ref_center

    prev_angle = ref_angle

    for frame in sorted(df["frame"].unique()):
        frame_df = df[df["frame"] == frame]

        cur_base = get_point(frame_df, "back_base")
        cur_end = get_point(frame_df, "back_end")

        if cur_base is None or cur_end is None:
            continue

        cur_center = 0.5 * (cur_base + cur_end)
        cur_vec = cur_end - cur_base
        cur_len = np.linalg.norm(cur_vec)

        # Wenn DLC die Rückenpunkte kollabieren lässt, benutze vorherige Richtung.
        if cur_len < args.min_body_len_factor * ref_len:
            cur_angle = prev_angle
        else:
            cur_angle = math.atan2(cur_vec[1], cur_vec[0])
            prev_angle = cur_angle

        R = rot2d(cur_angle - ref_angle)

        # Rekonstruiere Body-Nodes mit konstanter Referenzform.
        for node, offset in ref_offsets.items():
            new_xz = cur_center + R @ offset
            set_point(df, frame, node, new_xz)

    df.to_csv(args.out_csv, index=False)
    print("Saved:", args.out_csv)
    print("Reference frame:", args.ref_frame)
    print("Reference body length:", ref_len)


if __name__ == "__main__":
    main()