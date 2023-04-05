import os
from typing import Dict, List, Optional
import httpx
import asyncio
from model.web_result import WebResult

class BingSearch:
    def __init__(self, subscription_key: str = "", search_url: str = "", query_result_count: int = 3):
        self.subscription_key = subscription_key or os.environ.get("BING_SUBSCRIPTION_KEY")
        self.search_url = search_url or os.environ.get("BING_SEARCH_URL", "https://api.bing.microsoft.com/v7.0/search")
        self.query_result_count = query_result_count

    async def _bing_search_results(self, search_term: str, count: int) -> List[dict]:
        if not self.subscription_key:
            print("Error: subscription_key is not provided")
            return []

        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        params = {
            "q": search_term,
            "count": str(count),
            "textDecorations": "True",
            "textFormat": "HTML",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json()
            return search_results["webPages"]["value"]
        except Exception as e:
            print(f"Error fetching search results: {e}")
            return []

    async def results(self, query: str) -> List[WebResult]:
        web_results = []
        results = await self._bing_search_results(query, count=self.query_result_count)
        if len(results) == 0:
            return []

        for result in results:
            web_result = WebResult(
                id=result["id"],
                name=result["name"],
                url=result["url"],
                display_url=result["displayUrl"],
                snippet=result["snippet"],
                date_last_crawled=result["dateLastCrawled"],
                language=result["language"],
                is_navigational=result["isNavigational"],
                contractual_rules=result.get("contractualRules", []),
            )
            web_results.append(web_result)

        return web_results
