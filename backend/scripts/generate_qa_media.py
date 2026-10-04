"""Generate a labelled narrated test source, not product sample-data fallback."""

import argparse
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import get_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Use a new output path; existing media will not be overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    narration = (
        "This is a labelled Creator AI integration test. First, improve your camera setup. "
        "Place your camera at eye level and use soft lighting to make your face clear. "
        "Next, improve the audio recording. Keep the microphone close and reduce background "
        "noise so viewers can hear your voice. Finally, demonstrate the product visually. "
        "Show the red product package on the blue background. A clear visual demonstration "
        "helps viewers understand your message. Save this production guide for your next video."
    )
    with TemporaryDirectory(prefix="creatorai-qa-narration-") as directory:
        audio = Path(directory) / "narration.aiff"
        subprocess.run(
            ["say", "-v", "Samantha", "-r", "130", "-o", str(audio), narration],
            check=True,
            capture_output=True,
            timeout=60,
        )
        subprocess.run(
            [
                get_settings().ffmpeg_binary,
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=640x360:r=30",
                "-i",
                str(audio),
                "-vf",
                "drawbox=x=220:y=80:w=200:h=200:color=red:t=fill,"
                "drawtext=font=Arial:text='LABELLED QA SOURCE':"
                "x=20:y=20:fontsize=25:fontcolor=white",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    print(f"Generated labelled, narrated QA media: {output}")


if __name__ == "__main__":
    main()
