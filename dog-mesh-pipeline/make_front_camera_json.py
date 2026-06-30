#!/usr/bin/env python3
"""Create a one-camera cameras.json for rendering pseudo-3D side/front-view coords."""
from __future__ import annotations
import argparse, json
from pathlib import Path


def video_size(path):
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        cap.release()
        return w, h, fps
    except Exception:
        return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--video", default=None)
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--distance", type=float, default=2000.0)
    ap.add_argument("--name", default="cam_front")
    args = ap.parse_args()
    vw, vh, _ = video_size(args.video) if args.video else (None, None, None)
    width = args.width or vw
    height = args.height or vh
    if width is None or height is None:
        raise SystemExit("Pass --video or both --width and --height")
    world_w = width * args.scale
    world_h = height * args.scale
    # World: X right, Y depth, Z up. Camera at (world_w/2, -distance, world_h/2), looking along +Y.
    # OpenCV camera coords: x right, y down, z forward.
    R = [[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]
    t = [-world_w / 2.0, world_h / 2.0, args.distance]
    focal = args.distance / args.scale
    data = {
        "cameras": [{
            "name": args.name,
            "width": int(width),
            "height": int(height),
            "fx": float(focal),
            "fy": float(focal),
            "cx": float(width) / 2.0,
            "cy": float(height) / 2.0,
            "R": R,
            "t": t,
            "pos_world": [world_w / 2.0, -args.distance, world_h / 2.0]
        }]
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")

if __name__ == "__main__":
    main()
