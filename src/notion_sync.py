import os
import json
import requests
from typing import Dict, Optional
from datetime import datetime, timezone
from .config import NOTION_TOKEN, NOTION_DB_ID, NOTION_BASE, NOTION_VERSION


def create_notion_page(reel_data: Dict, meta: Dict, pending: Dict) -> Optional[str]:
    """
    Crée une page Notion pour un reel traité.
    Retourne l'ID de la page Notion ou None en cas d'erreur.
    """
    if not NOTION_TOKEN or not NOTION_DB_ID:
        print("[NOTION] Pas de token ou DB_ID configuré, skip sync")
        return None

    try:
        # Préparer les tags pour Notion
        tags = []
        for tag in (reel_data.get("tags") or []):
            tags.append({"name": tag})

        # Tronquer les champs trop longs pour Notion
        def truncate(text: str, max_len: int = 2000) -> str:
            return (text or "")[:max_len]

        props = {
            "Nom": {
                "title": [{"text": {"content": truncate(meta.get("title") or meta.get("uploader") or "Reel")}}]
            },
            "URL": {
                "url": pending["url"]
            },
            "Plateforme": {
                "select": {"name": pending["platform"].capitalize()}
            },
            "Créateur": {
                "rich_text": [{"text": {"content": truncate(meta.get("uploader") or "")}}]
            },
            "Catégorie": {
                "select": {"name": reel_data.get("category") or "Autre"}
            },
            "Tags": {
                "multi_select": tags
            },
            "Résumé": {
                "rich_text": [{"text": {"content": truncate(reel_data.get("summary") or "")}}]
            },
            "Points clés": {
                "rich_text": [{"text": {"content": truncate(json.dumps(reel_data.get("key_points", []), ensure_ascii=False))}}]
            },
            "Transcription": {
                "rich_text": [{"text": {"content": truncate(reel_data.get("transcript") or "")}}]
            },
            "Langue": {
                "select": {"name": (reel_data.get("language") or "autre").capitalize()}
            },
            "Vision ?": {
                "checkbox": bool(reel_data.get("needs_vision"))
            },
            "ID Reel": {
                "number": reel_data.get("reel_id")
            },
            "Date de traitement": {
                "date": {"start": datetime.now(timezone.utc).isoformat()}
            }
        }

        # Créer la page
        response = requests.post(
            f"{NOTION_BASE}/pages",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json"
            },
            json={
                "parent": {"database_id": NOTION_DB_ID},
                "properties": props
            },
            timeout=30
        )

        if response.ok:
            return response.json().get("id")
        else:
            print(f"[NOTION ERR] {response.status_code}: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"[NOTION ERR] Exception: {str(e)}")
        return None
