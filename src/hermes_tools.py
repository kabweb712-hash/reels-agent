"""
Tools Hermès pour Reels Agent — Compatible OpenRouter Function Calling
Chaque fonction est appelée par Jarvis 4 (Hermès) via OpenRouter.
"""

import os
import json
import sqlite3
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime
from .config import DB_PATH, PROJECT_ROOT
from .db import (
    get_conn, ensure_categories, category_id, detect_platform,
    get_pending_reels, get_category_suggestions, promote_category
)


# ============================================================
# TOOL 1: enqueue_reel
# ============================================================
def enqueue_reel(url: str, note: Optional[str] = None, platform: Optional[str] = None) -> Dict[str, Any]:
    """
    Enregistre un lien de reel dans la queue de traitement.
    Appelé quand l'utilisateur partage une URL via Telegram.
    """
    try:
        if not url or not isinstance(url, str):
            return {"error": "URL manquante ou invalide"}

        platform = platform or detect_platform(url)
        conn = get_conn()
        ensure_categories(conn)

        conn.execute("""
            INSERT INTO pending_reels(url, platform, user_note, status, added_at)
            VALUES (?, ?, ?, 'pending', datetime('now'))
        """, (url, platform, note))
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"✅ Reel ajouté à la queue. Traitement prévu cette nuit à 3h.",
            "url": url,
            "platform": platform
        }
    except sqlite3.IntegrityError:
        return {"error": f"Ce reel est déjà en queue ou traité: {url}"}
    except Exception as e:
        return {"error": f"Erreur: {str(e)}"}


# ============================================================
# TOOL 2: query_reels
# ============================================================
def query_reels(
    keywords: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    since_days: Optional[int] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Recherche dans les reels déjà traités.
    Utilise FTS5 sur transcript + summary.
    """
    try:
        conn = get_conn()
        query = """
            SELECT r.id, r.url, r.platform, r.creator, r.title,
                   r.summary, r.key_points, r.tags,
                   c.name as category_name,
                   r.needs_vision, r.processed_at, r.notion_page_id
            FROM reels r
            LEFT JOIN categories c ON r.category_id = c.id
        """
        params = []

        # Filtres WHERE
        conditions = []
        if keywords:
            conditions.append("(r.id IN (SELECT rowid FROM reels_fts WHERE transcript MATCH ? OR summary MATCH ?))")
            params.extend([keywords, keywords])

        if category:
            conditions.append("c.name = ?")
            params.append(category)

        if tags:
            for tag in tags:
                conditions.append(f"r.tags LIKE ?")
                params.append(f'%"{tag}"%')

        if since_days:
            conditions.append("r.processed_at >= datetime('now', ?)")
            params.append(f"-{since_days} days")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY r.processed_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        # Formattage
        results = []
        for row in rows:
            try:
                key_points = json.loads(row["key_points"]) if row["key_points"] else []
                tags = json.loads(row["tags"]) if row["tags"] else []
            except:
                key_points = []
                tags = []

            results.append({
                "id": row["id"],
                "url": row["url"],
                "platform": row["platform"],
                "creator": row["creator"],
                "title": row["title"],
                "category": row["category_name"],
                "summary": row["summary"],
                "key_points": key_points,
                "tags": tags,
                "needs_vision": bool(row["needs_vision"]),
                "notion_url": f"https://notion.so/{row['notion_page_id']}" if row["notion_page_id"] else None
            })

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOOL 3: list_pending_reels
# ============================================================
def list_pending_reels() -> Dict[str, Any]:
    """Affiche l'état de la queue de traitement."""
    try:
        conn = get_conn()
        rows = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM pending_reels
            GROUP BY status
        """).fetchall()
        conn.close()

        stats = {row["status"]: row["count"] for row in rows}
        return {
            "status": "success",
            "queue": {
                "pending": stats.get("pending", 0),
                "processing": stats.get("processing", 0),
                "done": stats.get("done", 0),
                "failed": stats.get("failed", 0)
            }
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOOL 4: list_categories
# ============================================================
def list_categories() -> Dict[str, Any]:
    """Liste toutes les catégories + suggestions en attente."""
    try:
        conn = get_conn()

        # Catégories existantes
        categories = conn.execute("""
            SELECT id, name, type, usage_count
            FROM categories
            ORDER BY type DESC, usage_count DESC
        """).fetchall()

        # Suggestions en attente
        suggestions = get_category_suggestions(conn, "pending")

        conn.close()

        return {
            "status": "success",
            "categories": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "type": c["type"],
                    "usage_count": c["usage_count"]
                } for c in categories
            ],
            "pending_suggestions": [
                {
                    "id": s["id"],
                    "name": s["suggested_name"],
                    "proposed_at": s["proposed_at"]
                } for s in suggestions
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOOL 5: accept_category
# ============================================================
def accept_category(name: Optional[str] = None, suggestion_id: Optional[int] = None) -> Dict[str, Any]:
    """Valide une catégorie suggérée par l'IA."""
    try:
        if not name and not suggestion_id:
            return {"error": "Il faut fournir soit un nom, soit un suggestion_id"}

        conn = get_conn()

        if suggestion_id:
            # Récupérer le nom depuis la suggestion
            suggestion = conn.execute(
                "SELECT suggested_name FROM category_suggestions WHERE id = ?",
                (suggestion_id,)
            ).fetchone()
            if not suggestion:
                return {"error": f"Suggestion #{suggestion_id} introuvable"}
            name = suggestion["suggested_name"]

        # Vérifier que la catégorie n'existe pas déjà
        existing = conn.execute(
            "SELECT id FROM categories WHERE name = ?",
            (name,)
        ).fetchone()
        if existing:
            return {"error": f"La catégorie '{name}' existe déjà"}

        # Promouvoir la catégorie
        new_cat_id = promote_category(conn, name)

        # Marquer la suggestion comme acceptée
        if suggestion_id:
            conn.execute(
                "UPDATE category_suggestions SET status = 'accepted' WHERE id = ?",
                (suggestion_id,)
            )
            conn.commit()

        conn.close()
        return {
            "status": "success",
            "message": f"✅ Catégorie '{name}' promue avec succès!",
            "category_id": new_cat_id
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOOL 6: trigger_batch
# ============================================================
def trigger_batch() -> Dict[str, Any]:
    """Déclenche manuellement le batch processor."""
    try:
        batch_path = os.path.join(PROJECT_ROOT, "src", "batch_processor.py")
        result = subprocess.run(
            ["python", batch_path],
            capture_output=True,
            text=True,
            timeout=3600,  # 1h max
            cwd=PROJECT_ROOT
        )

        if result.returncode == 0:
            processed = result.stdout.count("[OK]") if result.stdout else 0
            return {
                "status": "success",
                "message": f"✅ Batch terminé! {processed} reels traités.",
                "output": result.stdout[:1000]
            }
        else:
            return {
                "status": "error",
                "error": f"Batch échoué: {result.stderr[:500]}"
            }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout après 1h"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOOL 7: get_reel_detail
# ============================================================
def get_reel_detail(reel_id: int) -> Dict[str, Any]:
    """Récupère le détail complet d'un reel."""
    try:
        conn = get_conn()
        reel = conn.execute("""
            SELECT r.*, c.name as category_name
            FROM reels r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.id = ?
        """, (reel_id,)).fetchone()
        conn.close()

        if not reel:
            return {"error": f"Reel #{reel_id} introuvable"}

        try:
            key_points = json.loads(reel["key_points"]) if reel["key_points"] else []
            tags = json.loads(reel["tags"]) if reel["tags"] else []
            raw_metadata = json.loads(reel["raw_metadata"]) if reel["raw_metadata"] else {}
        except:
            key_points = []
            tags = []
            raw_metadata = {}

        return {
            "status": "success",
            "reel": {
                "id": reel["id"],
                "url": reel["url"],
                "platform": reel["platform"],
                "creator": reel["creator"],
                "title": reel["title"],
                "thumbnail_url": reel["thumbnail_url"],
                "duration_sec": reel["duration_sec"],
                "language": reel["language"],
                "transcript": reel["transcript"],
                "summary": reel["summary"],
                "key_points": key_points,
                "category": reel["category_name"],
                "tags": tags,
                "needs_vision": bool(reel["needs_vision"]),
                "vision_analysis": reel["vision_analysis"],
                "raw_metadata": raw_metadata,
                "notion_url": f"https://notion.so/{reel['notion_page_id']}" if reel["notion_page_id"] else None,
                "processed_at": reel["processed_at"]
            }
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# EXPORT DES TOOLS POUR OPENROUTER
# ============================================================
TOOLS = {
    "enqueue_reel": enqueue_reel,
    "query_reels": query_reels,
    "list_pending_reels": list_pending_reels,
    "list_categories": list_categories,
    "accept_category": accept_category,
    "trigger_batch": trigger_batch,
    "get_reel_detail": get_reel_detail
}
