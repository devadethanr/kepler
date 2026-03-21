from __future__ import annotations


class NewsSearchTool:
    def search_news(self, query: str) -> dict[str, object]:
        return {"query": query, "results": [], "source": "not_configured"}
