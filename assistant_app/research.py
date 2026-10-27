"""Key-free Wikipedia research. Fixed endpoints prevent arbitrary URL fetches."""

import httpx


async def research(query: str):
    sources = []
    async with httpx.AsyncClient(
        timeout=20, headers={"User-Agent": "AtlasDesktop/0.1 (local personal research)"}
    ) as http:
        response = await http.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 3,
                "prop": "extracts|info",
                "explaintext": 1,
                "exintro": 1,
                "inprop": "url",
            },
        )
        response.raise_for_status()
        for page in response.json().get("query", {}).get("pages", {}).values():
            if page.get("extract") and page.get("fullurl"):
                sources.append({"title": page["title"], "url": page["fullurl"], "text": page["extract"][:6000]})
    return sources
