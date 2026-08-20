#!/usr/bin/env python3
"""
Reels Batch Processor — Worker cron (ex: 0 3 * * *)
Pipeline: pending_reels -> yt-dlp -> Groq Whisper -> Groq Llama -> SQLite -> Notion
"""

import os
import json
import tempfile
import traceback
from datetime import datetime
from .config import BATCH_LIMIT, MAX_RETRIES, PROJECT_ROOT
from .db import (
    get_conn, ensure_categories, get_pending_reels,
    mark_pending_as_processing, mark_pending_as_done,
    mark_pending_as_failed, category_id, reel_exists,
    increment_category_usage, add_category_suggestion
)
from .downloader import fetch_metadata, download_audio
from .transcriber import transcribe_audio
from .analyzer import analyze_transcript, format_analysis_result
from .notion_sync import create_notion_page


def process_one(conn, pending: Dict) -> bool:
    """
    Traite un seul reel (de la queue pending).
    Retourne True si succès, False sinon.
    """
    url = pending["url"]
    pending_id = pending["id"]

    try:
        # === Étape 1: Anti-doublon ===
        if reel_exists(conn, url):
            print(f"[SKIP] Déjà traité: {url}")
            mark_pending_as_done(conn, pending_id, None)
            return True

        # === Étape 2: Récupérer métadonnées ===
        print(f"[INFO] Traitement de: {url}")
        meta = fetch_metadata(url)
        platform = pending.get("platform") or "instagram"

        # === Étape 3: Télécharger audio ===
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = download_audio(url, tmpdir)
            if not audio_path:
                raise Exception("Échec du téléchargement audio")

            # === Étape 4: Transcription ===
            transcript = transcribe_audio(audio_path)
            if not transcript:
                print(f"[WARN] Transcript vide pour {url}")
                transcript = ""

            # === Étape 5: Analyse LLM ===
            analysis = analyze_transcript(transcript)
            formatted = format_analysis_result(transcript, analysis)

            # === Étape 6: Résoudre la catégorie ===
            cat_name = formatted["category"]
            cat_id = category_id(conn, cat_name)
            if not cat_id:
                cat_id = category_id(conn, "Autre")
                formatted["category"] = "Autre"

            # === Étape 7: Insérer dans reels ===
            cur = conn.execute("""
                INSERT INTO reels
                (url, platform, creator, title, thumbnail_url, duration_sec, language,
                 transcript, summary, key_points, category_id, tags, needs_vision, raw_metadata, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                url,
                platform,
                meta.get("uploader"),
                meta.get("title"),
                meta.get("thumbnail"),
                int(meta.get("duration") or 0),
                formatted["language"],
                formatted["transcript"],
                formatted["summary"],
                formatted["key_points"],
                cat_id,
                formatted["tags"],
                formatted["needs_vision"],
                json.dumps(meta, ensure_ascii=False)[:5000]
            ))
            reel_id = cur.lastrowid

            # === Étape 8: Gérer les suggestions de catégorie ===
            if formatted["category"] == "Autre" and formatted.get("suggested_category"):
                add_category_suggestion(conn, formatted["suggested_category"], reel_id)

            # === Étape 9: Sync Notion ===
            notion_id = create_notion_page(
                reel_data={
                    "reel_id": reel_id,
                    **formatted
                },
                meta=meta,
                pending=pending
            )

            # === Étape 10: Mettre à jour le reel avec notion_id ===
            if notion_id:
                conn.execute(
                    "UPDATE reels SET notion_page_id = ?, notion_synced_at = datetime('now') WHERE id = ?",
                    (notion_id, reel_id)
                )

            # === Étape 11: Finaliser ===
            mark_pending_as_done(conn, pending_id, reel_id)
            increment_category_usage(conn, cat_id)
            conn.commit()

            print(f"[OK] Reel #{reel_id} traité — Catégorie: {cat_name} — {url}")
            return True

    except Exception as e:
        error_msg = f"[ERR] {url}: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        mark_pending_as_failed(conn, pending_id, error_msg)
        conn.commit()
        return False


def main():
    """Point d'entrée du batch processor."""
    conn = get_conn()
    ensure_categories(conn)

    # Récupérer les reels en attente
    pending_list = get_pending_reels(conn, BATCH_LIMIT)
    print(f"[START] {len(pending_list)} reels à traiter")

    for pending in pending_list:
        # Marquer comme "processing" avant de commencer
        mark_pending_as_processing(conn, pending["id"])
        conn.commit()

        # Traiter le reel (avec retries si besoin)
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                success = process_one(conn, pending)
                if success:
                    break
                print(f"[RETRY] Tentative {attempt + 1}/{MAX_RETRIES} pour {pending['url']}")
            except Exception as e:
                print(f"[RETRY ERR] {pending['url']}: {str(e)}")

        if not success:
            print(f"[FAILED] Après {MAX_RETRIES} tentatives: {pending['url']}")

    conn.close()
    print("[END] Batch terminé")


if __name__ == "__main__":
    main()
