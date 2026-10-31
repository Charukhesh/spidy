"""Web Search & Grounded Web Verification Engine for Athena.

Provides:
1. Browser Tab Opener: Automatically opens Google Search in the default web browser.
2. Lightweight Web Search Scraper: Fetches live top search snippets without external API keys.
3. Verification Context Formatter: Formats web evidence into prompt-ready context for Gemini.
"""

import re
import html
import logging
import urllib.parse
import webbrowser
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger("athena.web_search")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class WebSearchEngine:
    """Handles real-time search queries and browser integration."""

    @staticmethod
    def open_in_browser(query: str) -> bool:
        """Open a new tab with Google Search in the user's default browser."""
        try:
            encoded_query = urllib.parse.quote_plus(query.strip())
            search_url = f"https://www.google.com/search?q={encoded_query}"
            logger.info(f"Opening browser search: {search_url}")
            webbrowser.open_new_tab(search_url)
            return True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False

    @staticmethod
    def search(query: str, max_results: int = 4, timeout: float = 6.0) -> List[Dict[str, str]]:
        """Search the web and extract top titles, snippets, and source URLs.
        
        Returns:
            List of dicts: [{"title": ..., "snippet": ..., "url": ...}]
        """
        results: List[Dict[str, str]] = []
        clean_q = query.strip()
        if not clean_q:
            return results

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # 1. Primary: DuckDuckGo HTML endpoint
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": clean_q},
                    headers=headers,
                )
                if resp.status_code == 200:
                    results = WebSearchEngine._parse_duckduckgo_html(resp.text, max_results)
                    if results:
                        logger.info(f"Retrieved {len(results)} web search results for '{clean_q}'")
                        return results
        except Exception as e:
            logger.debug(f"DuckDuckGo search notice: {e}")

        # 2. Secondary fallback: DuckDuckGo Instant Answer API
        try:
            encoded = urllib.parse.quote_plus(clean_q)
            api_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText", "")
                    heading = data.get("Heading", clean_q)
                    source_url = data.get("AbstractURL", "")
                    if abstract:
                        results.append({
                            "title": heading,
                            "snippet": abstract,
                            "url": source_url or "https://duckduckgo.com",
                        })
                        return results
        except Exception as e:
            logger.debug(f"Instant Answer API notice: {e}")

        return results

    @staticmethod
    def _parse_duckduckgo_html(html_text: str, max_results: int) -> List[Dict[str, str]]:
        """Parse result blocks from DuckDuckGo HTML output."""
        items: List[Dict[str, str]] = []
        
        # Pattern for search results
        pattern = re.compile(
            r'<h2 class="result__title">.*?<a class="result__url"[^>]*href="([^"]+)".*?>(.*?)</a>.*?'
            r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>',
            re.DOTALL,
        )

        # Simplified pattern matching snippets and titles
        title_pattern = re.compile(r'<a class="result__url"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', re.DOTALL)

        urls_and_titles = title_pattern.findall(html_text)
        snippets = snippet_pattern.findall(html_text)

        count = min(len(snippets), max_results)
        for i in range(count):
            raw_snippet = snippets[i]
            clean_snippet = html.unescape(re.sub(r"<[^>]+>", "", raw_snippet)).strip()
            
            raw_url = urls_and_titles[i][0] if i < len(urls_and_titles) else ""
            raw_title = urls_and_titles[i][1] if i < len(urls_and_titles) else f"Result {i+1}"
            clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()

            if clean_snippet:
                items.append({
                    "title": clean_title or f"Result {i+1}",
                    "snippet": clean_snippet,
                    "url": raw_url,
                })

        return items

    @staticmethod
    def format_for_prompt(results: List[Dict[str, str]]) -> str:
        """Format list of search results into clear prompt context."""
        if not results:
            return ""
        lines = ["Verified Web Search Results:"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['title']}] {r['snippet']}")
        return "\n".join(lines)


# Singleton instance
web_search = WebSearchEngine()

