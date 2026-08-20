import os
from pathlib import Path

# === Chemins ===
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "reels.db"))

# === OpenRouter (Hermès) ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
HERMES_MODEL = os.getenv("HERMES_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

# === Groq (Batch) ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = "https://api.groq.com/openai/v1"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "llama-3.1-8b-instant")

# === Notion ===
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# === Batch ===
BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "50"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = 120  # secondes

# === Catégories fixes (taxonomie initiale) ===
FIXED_CATEGORIES = [
    "Dev / IA",
    "Business", 
    "Motivation",
    "Lifestyle",
    "Sorties / Adresses",
    "Fitness",
    "Autre"
]

# === Plateformes supportées (inclut Facebook) ===
PLATFORMS = ["instagram", "tiktok", "youtube", "x", "facebook"]

# === Prompt système pour l'analyse LLM ===
SYSTEM_PROMPT = """Tu es un analyste de contenu vidéo. On te donne la transcription d'un reel (Instagram/TikTok/YouTube/Facebook/X).
Réponds EN JSON STRICT avec EXACTEMENT ces clés (et aucune autre) :
{{
    "summary": "résumé court en français (2-3 phrases max)",
    "key_points": ["liste", "de 3 à 5 points clés", "en français"],
    "category": "une catégorie parmi {cats} (ou 'Autre' si aucune ne convient)",
    "suggested_category": null si category != "Autre", sinon un nom court de catégorie proposé (ex: 'Recettes')
    "tags": ["tag1", "tag2", "tag3"],
    "needs_vision": true si le visuel semble important (démo, texte à l'écran, peu d'audio), sinon false,
    "language": "fr" ou "en" ou "autre"
}}
Tout doit être en français. Ne réponds JAMAIS en texte libre, SEULEMENT en JSON valide."""
