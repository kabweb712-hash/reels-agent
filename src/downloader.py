import os
import json
import subprocess
import tempfile
from typing import Dict, Optional
from .config import PROJECT_ROOT


def fetch_metadata(url: str) -> Dict:
    """Récupère les métadonnées d'un reel via yt-dlp (--dump-json)."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", url],
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Exception(f"yt-dlp metadata failed: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON from yt-dlp")


def download_audio(url: str, output_dir: str) -> Optional[str]:
    """Télécharge l'audio d'un reel en MP3 via yt-dlp."""
    try:
        template = os.path.join(output_dir, "%(title)s.%(ext)s")
        subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", template,
                "--no-playlist",
                url
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True
        )
        
        for f in os.listdir(output_dir):
            if f.endswith(".mp3"):
                return os.path.join(output_dir, f)
        return None
    except subprocess.CalledProcessError as e:
        raise Exception(f"yt-dlp audio download failed: {e.stderr}")


def get_video_info(url: str) -> Dict:
    """Récupère les infos essentielles d'une vidéo."""
    meta = fetch_metadata(url)
    return {
        "uploader": meta.get("uploader", meta.get("channel", "Unknown")),
        "title": meta.get("title", meta.get("fulltitle", "Untitled")),
        "thumbnail": meta.get("thumbnail"),
        "duration": meta.get("duration"),
        "platform": meta.get("extractor", "unknown"),
        "url": url
    }
