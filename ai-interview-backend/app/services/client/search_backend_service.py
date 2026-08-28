import asyncio
import base64
import json
import logging
from math import ceil
from typing import Dict, List, Optional
from urllib import request

from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchBackendService:
    @staticmethod
    async def search_learning_notes(
        keyword: str,
        user_id: Optional[int],
        note_type: Optional[str],
        page: int,
        size: int,
        scope: str,
    ) -> Optional[Dict]:
        if settings.SEARCH_BACKEND.lower() != "opensearch" or not settings.OPENSEARCH_URL:
            return None

        filters = []
        if scope == "my" and user_id:
            filters.append({"term": {"user_id": user_id}})
        elif scope == "public":
            filters.extend([
                {"term": {"visibility": "public"}},
                {"term": {"status": "published"}},
            ])
        if note_type:
            filters.append({"term": {"note_type": note_type}})

        body = {
            "from": (page - 1) * size,
            "size": size,
            "query": {
                "bool": {
                    "must": [{
                        "multi_match": {
                            "query": keyword,
                            "fields": ["title^3", "summary^2", "content", "tags"],
                        }
                    }],
                    "filter": filters,
                }
            },
            "highlight": {"fields": {"content": {"fragment_size": 120, "number_of_fragments": 1}}},
        }

        try:
            payload = await asyncio.to_thread(SearchBackendService._post_json, "_search", body)
        except Exception as exc:
            logger.warning("OpenSearch 检索失败，降级使用 PostgreSQL: %s", exc)
            return None

        hits = payload.get("hits", {})
        total_value = hits.get("total", {})
        total = total_value.get("value", 0) if isinstance(total_value, dict) else int(total_value or 0)
        items = []
        for hit in hits.get("hits", []):
            source = hit.get("_source", {})
            highlight = hit.get("highlight", {})
            items.append({
                "id": source.get("id"),
                "title": source.get("title", ""),
                "note_type": source.get("note_type", ""),
                "tags": source.get("tags"),
                "view_count": source.get("view_count", 0),
                "like_count": source.get("like_count", 0),
                "relevance": float(hit.get("_score") or 0),
                "headline": (highlight.get("content") or [source.get("summary") or ""])[0],
                "created_at": source.get("created_at"),
            })

        return {
            "items": items,
            "total": total,
            "per_page": size,
            "current_page": page,
            "last_page": ceil(total / size) if size > 0 else 0,
            "has_more": page < ceil(total / size) if size > 0 and total > 0 else False,
        }

    @staticmethod
    async def rerank_notes(keyword: str, items: List[Dict]) -> List[Dict]:
        if not settings.RERANKER_URL or len(items) < 2:
            return items

        documents = [
            " ".join(filter(None, [str(item.get("title") or ""), str(item.get("headline") or "")]))
            for item in items
        ]
        body = {"query": keyword, "documents": documents}

        try:
            payload = await asyncio.to_thread(SearchBackendService._post_reranker, body)
        except Exception as exc:
            logger.warning("Reranker 服务失败，保留原排序: %s", exc)
            return items

        scores = payload.get("scores")
        if isinstance(scores, list) and len(scores) == len(items):
            ranked = []
            for item, score in zip(items, scores):
                next_item = dict(item)
                next_item["rerank_score"] = float(score)
                ranked.append(next_item)
            return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)

        results = payload.get("results")
        if isinstance(results, list):
            ordered = []
            for result in results:
                index = result.get("index")
                if isinstance(index, int) and 0 <= index < len(items):
                    next_item = dict(items[index])
                    if "score" in result:
                        next_item["rerank_score"] = float(result["score"])
                    ordered.append(next_item)
            if ordered:
                return ordered

        return items

    @staticmethod
    def _post_json(path: str, body: Dict) -> Dict:
        base_url = settings.OPENSEARCH_URL.rstrip("/")
        index = settings.OPENSEARCH_INDEX.strip("/")
        return SearchBackendService._post(f"{base_url}/{index}/{path}", body, settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)

    @staticmethod
    def _post_reranker(body: Dict) -> Dict:
        return SearchBackendService._post(settings.RERANKER_URL, body, "", "")

    @staticmethod
    def _post(url: str, body: Dict, username: str, password: str) -> Dict:
        data = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        if username and password:
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            req.add_header("Authorization", f"Basic {token}")
        with request.urlopen(req, timeout=settings.RERANKER_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))


search_backend_service = SearchBackendService()
