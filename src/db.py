import sqlite3
import json
from typing import Optional, List, Dict, Any
from .config import DB_PATH, FIXED_CATEGORIES


def get_conn():
    """Retourne une connexion SQLite avec foreign_keys et WAL activés."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def ensure_categories(conn):
    """S'assure que les catégories fixes existent."""
    for name in FIXED_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO categories(name, type) VALUES (?, 'fixed')",
            (name,)
        )
    conn.commit()


def category_id(conn, name: str) -> Optional[int]:
    """Récupère l'ID d'une catégorie par son nom."""
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?",
        (name,)
    ).fetchone()
    return row["id"] if row else None


def detect_platform(url: str) -> str:
    """Détecte la plateforme depuis une URL (inclut Facebook)."""
    url_lower = url.lower()
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "x"
    return "instagram"


def reel_exists(conn, url: str) -> bool:
    """Vérifie si un reel existe déjà dans la DB (anti-doublon)."""
    return conn.execute(
        "SELECT 1 FROM reels WHERE url = ?",
        (url,)
    ).fetchone() is not None


def get_pending_reels(conn, limit: int = 50) -> List[Dict[str, Any]]:
    """Récupère les reels en attente de traitement (status=pending)."""
    rows = conn.execute(
        """SELECT * FROM pending_reels
           WHERE status = 'pending'
           ORDER BY added_at
           LIMIT ?""",
        (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def mark_pending_as_processing(conn, pending_id: int):
    """Marque un pending_reel comme 'processing'."""
    conn.execute(
        "UPDATE pending_reels SET status = 'processing' WHERE id = ?",
        (pending_id,)
    )
    conn.commit()


def mark_pending_as_done(conn, pending_id: int, reel_id: int):
    """Marque un pending_reel comme 'done' avec lien vers reel_id."""
    conn.execute(
        "UPDATE pending_reels SET status = 'done', reel_id = ? WHERE id = ?",
        (reel_id, pending_id)
    )
    conn.commit()


def mark_pending_as_failed(conn, pending_id: int, error: str):
    """Marque un pending_reel comme 'failed' avec l'erreur."""
    conn.execute(
        "UPDATE pending_reels SET status = 'failed', error = ? WHERE id = ?",
        (str(error)[:500], pending_id)
    )
    conn.commit()


def increment_category_usage(conn, category_id: int):
    """Incrémente le compteur d'utilisation d'une catégorie."""
    conn.execute(
        "UPDATE categories SET usage_count = usage_count + 1 WHERE id = ?",
        (category_id,)
    )
    conn.commit()


def add_category_suggestion(conn, suggested_name: str, reel_id: int):
    """Ajoute une suggestion de catégorie (quand category='Autre')."""
    conn.execute(
        """INSERT INTO category_suggestions(suggested_name, reel_id, status)
           VALUES (?, ?, 'pending')""",
        (suggested_name, reel_id)
    )
    conn.commit()


def get_category_suggestions(conn, status: str = "pending") -> List[Dict[str, Any]]:
    """Récupère les suggestions de catégories par statut."""
    rows = conn.execute(
        """SELECT id, suggested_name, reel_id, status, proposed_at
           FROM category_suggestions
           WHERE status = ?
           ORDER BY proposed_at DESC""",
        (status,)
    ).fetchall()
    return [dict(row) for row in rows]


def promote_category(conn, name: str):
    """Promeut une suggestion en catégorie 'promoted'. Retourne l'ID."""
    conn.execute(
        """INSERT OR IGNORE INTO categories(name, type, created_at)
           VALUES (?, 'promoted', datetime('now'))""",
        (name,)
    )
    conn.commit()
    return category_id(conn, name)
