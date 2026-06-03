"""
VYNTRA AI Search — Full-text search over educational materials.

Provides RAG (Retrieval-Augmented Generation) capability for the AI tutor.
"""

import json
import logging
from typing import Any

from supabase import Client

logger = logging.getLogger("siee.ai_search")


async def search_materials(db: Client, args: dict[str, Any], user_id: str) -> str:
    """Search educational materials and guides by text query.

    Uses PostgreSQL full-text search (tsvector) on class_materials markdown
    content and guides titles/descriptions. Returns ranked results.
    """
    query = args.get("query", "").strip()
    max_results = min(int(args.get("max_results", 5)), 10)

    if not query or len(query) < 3:
        return json.dumps({"error": "La consulta debe tener al menos 3 caracteres."}, ensure_ascii=False)

    try:
        result = db.rpc(
            "search_educational_materials",
            {"search_query": query, "max_results": max_results},
        ).execute()

        items = result.data if result.data else []
        if not items:
            return json.dumps({
                "query": query,
                "count": 0,
                "results": [],
                "message": f"No se encontraron resultados para '{query}'. Intenta con otros términos.",
            }, ensure_ascii=False)

        formatted = []
        for item in items:
            formatted.append({
                "type": item.get("source_type", "material"),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("url", ""),
                "subject": item.get("subject_name", ""),
                "grade": item.get("grade", ""),
            })

        return json.dumps({
            "query": query,
            "count": len(formatted),
            "results": formatted,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error("search_materials error: %s", e)
        return json.dumps({
            "error": "Error al buscar materiales. Intenta de nuevo.",
            "detail": str(e)[:100],
        }, ensure_ascii=False)
