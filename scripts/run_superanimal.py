"""
Runs the DeepLabCut model with option to specify model, detector and more.
Only necessary input is the path to the input video
"""

# TODO: alle flags entfernen und model etc direkt übergeben -> brauche die flags eh nciht und so ist es einfacher

import argparse
from pathlib import Path
import deeplabcut

def parse_args():
    parser = argparse.ArgumentParser(description="Run DeepLabCut SuperAnimal inference on a video.")
    parser.add_argument("video_path", help="Pfad zum Video, z.B. /path/to/video.mp4")
    parser.add_argument("--superanimal-name", default="superanimal_quadruped")
    parser.add_argument("--model-name", default="hrnet_w32")
    parser.add_argument("--detector-name", default="fasterrcnn_resnet50_fpn_v2")
    parser.add_argument("--video-adapt", action="store_true", help="Aktiviert video_adapt=True")
    return parser.parse_args()


def main():
    args = parse_args()
    video_path = Path(args.video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_path}")

    deeplabcut.video_inference_superanimal(
        videos=[str(video_path)],
        superanimal_name=args.superanimal_name,
        model_name=args.model_name,
        detector_name=args.detector_name,
        video_adapt=args.video_adapt,
    )


if __name__ == "__main__":
    main()
