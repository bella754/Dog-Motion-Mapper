"""
Runs the DeepLabCut model
"""
import argparse
from pathlib import Path
import deeplabcut

def parse_args():
    parser = argparse.ArgumentParser(description="Run DeepLabCut SuperAnimal inference on a video.")
    parser.add_argument("video_path", help="Pfad zum Video, z.B. /path/to/video.mp4")
    return parser.parse_args()

def main():
    args = parse_args()
    video_path = Path(args.video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_path}")

    deeplabcut.video_inference_superanimal(
        videos=[str(video_path)],
        superanimal_name="superanimal_quadruped",
        model_name="hrnet_w32",
        detector_name="fasterrcnn_resnet50_fpn_v2",
        video_adapt="store_true",
    )

if __name__ == "__main__":
    main()
