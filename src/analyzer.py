import os
import json
import requests
from typing import Dict
from .config import (
    GROQ_API_KEY,
    GROQ_BASE,
    LLM_MODEL,
    FALLBACK_LLM_MODEL,
    SYSTEM_PROMPT,
    FIXED_CATEGORIES,
    REQUEST_TIMEOUT
)


def analyze_transcript(transcript: str) -> Dict:
    """
    Analyse un transcript via Groq Llama 3.3.
    Retourne un dict avec summary, key_points, category, etc.
    """
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY non configuré")

    # Préparer le prompt avec les catégories
    cats = ", ".join([f"'{c}'" for c in FIXED_CATEGORIES])
    prompt = SYSTEM_PROMPT.format(cats=cats)

    # Essayer avec le modèle principal d'abord, puis fallback
    for model in [LLM_MODEL, FALLBACK_LLM_MODEL]:
        try:
            response = requests.post(
                f"{GROQ_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": model,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": transcript or "(pas d'audio)"}
                    ]
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            continue  # Essayer le fallback

    raise Exception("Tous les modèles LLM ont échoué")


def format_analysis_result(transcript: str, analysis: Dict) -> Dict:
    """
    Formate le résultat de l'analyse pour stockage en DB.
    """
    return {
        "transcript": transcript,
        "summary": analysis.get("summary", ""),
        "key_points": json.dumps(analysis.get("key_points", []), ensure_ascii=False),
        "category": analysis.get("category", "Autre"),
        "suggested_category": analysis.get("suggested_category"),
        "tags": json.dumps(analysis.get("tags", []), ensure_ascii=False),
        "needs_vision": 1 if analysis.get("needs_vision", False) else 0,
        "language": analysis.get("language", "autre")
    }
