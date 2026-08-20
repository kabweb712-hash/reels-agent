import os
import requests
from typing import Optional
from .config import GROQ_API_KEY, GROQ_BASE, WHISPER_MODEL, REQUEST_TIMEOUT


def transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Transcrit un fichier audio via Groq Whisper.
    Retourne le texte transcrit ou None en cas d'erreur.
    """
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY non configuré")

    try:
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                f"{GROQ_BASE}/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": audio_file},
                data={
                    "model": WHISPER_MODEL,
                    "response_format": "json",
                    "language": "fr"  # Préférence pour le français
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("text", "").strip()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Groq Whisper API error: {str(e)}")
