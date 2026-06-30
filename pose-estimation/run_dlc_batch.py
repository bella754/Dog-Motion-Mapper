import argparse
import traceback
from pathlib import Path

import deeplabcut


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run DeepLabCut SuperAnimal inference on a list of videos."
    )

    parser.add_argument(
        "video_list",
        help=(
            "Textdatei mit einem Videopfad pro Zeile. "
            "Leere Zeilen und Zeilen mit # werden ignoriert."
        ),
    )

    parser.add_argument("--superanimal-name", default="superanimal_quadruped")
    parser.add_argument("--model-name", default="hrnet_w32")
    parser.add_argument("--detector-name", default="fasterrcnn_resnet50_fpn_v2")

    parser.add_argument(
        "--video-adapt",
        action="store_true",
        help="Aktiviert video_adapt=True. Kann besser sein, dauert aber länger.",
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Wenn ein Video fehlschlägt, mit dem nächsten weitermachen.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, welche Videos verarbeitet würden, aber DLC nicht starten.",
    )

    return parser.parse_args()


def read_video_list(video_list_path: Path) -> list[Path]:
    if not video_list_path.exists():
        raise FileNotFoundError(f"Videoliste nicht gefunden: {video_list_path}")

    base_dir = video_list_path.parent
    videos = []

    with video_list_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue
            if line.startswith("#"):
                continue

            video_path = Path(line).expanduser()

            # Relative Pfade werden relativ zur Videoliste interpretiert.
            if not video_path.is_absolute():
                video_path = base_dir / video_path

            video_path = video_path.resolve()

            if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
                print(
                    f"WARNUNG: Zeile {line_number}: Datei sieht nicht wie ein Video aus: {video_path}"
                )

            videos.append(video_path)

    return videos


def run_dlc(video_path: Path, args):
    print("\n" + "=" * 80)
    print(f"Starte DLC für: {video_path}")
    print("=" * 80)

    if not video_path.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_path}")

    deeplabcut.video_inference_superanimal(
        videos=[str(video_path)],
        superanimal_name=args.superanimal_name,
        model_name=args.model_name,
        detector_name=args.detector_name,
        video_adapt=args.video_adapt,
    )

    print(f"Fertig: {video_path}")


def main():
    args = parse_args()
    video_list_path = Path(args.video_list).expanduser().resolve()
    videos = read_video_list(video_list_path)

    if not videos:
        raise ValueError(f"Keine Videos in Liste gefunden: {video_list_path}")

    print(f"Videoliste: {video_list_path}")
    print(f"Gefundene Videos: {len(videos)}")
    print(f"video_adapt: {args.video_adapt}")

    for video_path in videos:
        print(f"  {video_path}")

    if args.dry_run:
        print("\nDry-run aktiv: DLC wurde nicht gestartet.")
        return

    successful = []
    failed = []

    for idx, video_path in enumerate(videos, start=1):
        print(f"\nVideo {idx}/{len(videos)}")

        try:
            run_dlc(video_path, args)
            successful.append(video_path)
        except Exception as exc:
            print(f"FEHLER bei Video: {video_path}")
            print(f"Fehlermeldung: {exc}")
            traceback.print_exc()
            failed.append(video_path)

            if not args.continue_on_error:
                print("\nAbbruch wegen Fehler. Nutze --continue-on-error, wenn das Skript weitermachen soll.")
                break

    print("\n" + "=" * 80)
    print("Zusammenfassung")
    print("=" * 80)
    print(f"Erfolgreich: {len(successful)}")
    for p in successful:
        print(f"  OK: {p}")

    print(f"Fehlgeschlagen: {len(failed)}")
    for p in failed:
        print(f"  FAIL: {p}")


if __name__ == "__main__":
    main()
