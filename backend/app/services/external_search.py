"""External medical knowledge search via SearXNG.

ExternalSearchAgent retrieves real-time medical guidelines, papers,
and drug information from authoritative external sources. Results are
NOT stored in the internal knowledge base — they are injected directly
into LLM prompts as supplementary context.

Design principles (from architecture docs):
- Search only, no storage
- Trust scoring with domain whitelist
- Admin-configurable parameters
- Fail gracefully (return empty results on error)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config import DynamicConfigService


@dataclass(frozen=True)
class SearchResult:
    """Single external search result with trust scoring."""

    title: str
    url: str
    snippet: str
    source_engine: str
    trust_score: int
    is_trusted: bool


class ExternalSearchAgent:
    """Agent for retrieving real-time external medical knowledge.

    Uses SearXNG JSON API to search guidelines, papers, and drug info.
    All results are scored for trustworthiness based on domain whitelist.
    """

    # ------------------------------------------------------------------
    # Trusted domain whitelist
    # ------------------------------------------------------------------
    TRUSTED_DOMAINS: frozenset[str] = frozenset({
        ".gov.cn",
        ".gov",
        ".edu.cn",
        ".edu",
        "who.int",
        "cdc.gov",
        "ncbi.nlm.nih.gov",
        "pubmed.ncbi.nlm.nih.gov",
        "cnki.net",
        "wanfangdata.com.cn",
        "medsci.cn",
        "dxy.cn",
        "nmpa.gov.cn",
        "chinacdc.cn",
        "cma.org.cn",           # 中华医学会
        "cmda.net",             # 中国医师协会
        "cmac.org.cn",          # 中国抗癌协会
        "csco.org.cn",          # 中国临床肿瘤学会
        "chestnet.org",         # 美国胸科医师学会
        "escardio.org",         # 欧洲心脏病学会
        "acc.org",              # 美国心脏病学会
        "ada.org",              # 美国糖尿病协会
        "idf.org",              # 国际糖尿病联盟
        "uptodate.com",         # UpToDate (if accessible)
        "bmj.com",
        "nejm.org",
        "jamanetwork.com",
        "thelancet.com",
        "cochrane.org",
        "nice.org.uk",
    })

    HIGH_TRUST_ENGINES: frozenset[str] = frozenset({
        "pubmed",
        "wikipedia",
        "google scholar",
        "google_scholar",
    })

    def __init__(self, base_url: str, timeout: int = 10) -> None:
        """Initialize with SearXNG endpoint.

        Args:
            base_url: SearXNG base URL (e.g. "http://searxng:8080")
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Factory: build from database config
    # ------------------------------------------------------------------

    @classmethod
    async def from_config(cls, db: AsyncSession) -> "ExternalSearchAgent":
        """Create an instance using current system settings."""
        base_url = await DynamicConfigService.get_str(
            db, "external_search.base_url", default="http://searxng:8080"
        )
        timeout = await DynamicConfigService.get_int(
            db, "external_search.timeout", default=10
        )
        return cls(base_url=base_url or "http://searxng:8080", timeout=timeout)

    # ------------------------------------------------------------------
    # Public search APIs
    # ------------------------------------------------------------------

    async def search_guidelines(
        self, disease: str, lang: str = "zh-CN"
    ) -> list[SearchResult]:
        """Search clinical guidelines for a disease.

        Query template: {disease} 临床指南 OR clinical guideline OR 诊疗规范 OR 专家共识
        """
        query = (
            f"{disease} 临床指南 OR clinical guideline OR 诊疗规范 OR 专家共识"
        )
        raw = await self._searxng_search(query, lang=lang)
        return self._filter_trusted(raw)

    async def search_drug_info(
        self, drug_name: str, lang: str = "zh-CN"
    ) -> list[SearchResult]:
        """Search drug information (instructions, pharmacology, adverse effects).

        Query template: {drug_name} 说明书 OR 药理作用 OR drug information OR 不良反应
        """
        query = (
            f"{drug_name} 说明书 OR 药理作用 OR drug information OR 不良反应"
        )
        raw = await self._searxng_search(query, lang=lang)
        return self._filter_trusted(raw)

    async def search_papers(
        self,
        topic: str,
        lang: str = "zh-CN",
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Search academic papers / clinical studies.

        Query template: {topic} 研究 OR 临床研究 OR randomized trial OR meta-analysis
        """
        query = (
            f"{topic} 研究 OR 临床研究 OR randomized trial OR meta-analysis"
        )
        raw = await self._searxng_search(query, lang=lang)
        filtered = self._filter_trusted(raw)
        return filtered[:max_results]

    async def healthcheck(self) -> dict[str, Any]:
        """Check SearXNG connectivity.

        Returns a dict with status and latency_ms.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use a simple search to verify JSON API is working
                url = f"{self.base_url}/search"
                params = {
                    "q": "healthcheck",
                    "format": "json",
                    "safesearch": "0",
                }
                start = asyncio.get_event_loop().time()
                resp = await client.get(url, params=params)
                latency_ms = round(
                    (asyncio.get_event_loop().time() - start) * 1000, 1
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "status": "ok",
                        "latency_ms": latency_ms,
                        "base_url": self.base_url,
                        "engines": data.get("engines", []),
                    }
                return {
                    "status": "error",
                    "latency_ms": latency_ms,
                    "base_url": self.base_url,
                    "http_status": resp.status_code,
                    "detail": resp.text[:200],
                }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "latency_ms": None,
                "base_url": self.base_url,
                "detail": f"Timeout after {self.timeout}s",
            }
        except Exception as exc:  # pragma: no cover
            return {
                "status": "error",
                "latency_ms": None,
                "base_url": self.base_url,
                "detail": str(exc)[:200],
            }

    # ------------------------------------------------------------------
    # Internal: SearXNG JSON API call
    # ------------------------------------------------------------------

    async def _searxng_search(
        self, query: str, lang: str = "zh-CN"
    ) -> list[dict[str, Any]]:
        """Call SearXNG JSON API and return raw result list.

        Returns empty list on any failure (network, timeout, parse error).
        """
        url = f"{self.base_url}/search"
        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "language": lang,
            "safesearch": "0",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("results", [])
        except Exception:
            # Fail gracefully — external search is supplementary, not critical
            return []

    # ------------------------------------------------------------------
    # Internal: trust scoring & filtering
    # ------------------------------------------------------------------

    def _filter_trusted(
        self, results: list[dict[str, Any]]
    ) -> list[SearchResult]:
        """Score and sort results by trustworthiness.

        Scoring:
        - +50 for trusted domain match
        - +30 for high-trust search engine (pubmed, wikipedia, etc.)
        - +10 for content length > 200 chars
        - +5 for content length > 50 chars
        """
        scored: list[SearchResult] = []
        for r in results:
            url = r.get("url", "")
            engine = (r.get("engine") or "").lower()
            content = r.get("content") or ""
            score = 0

            # 1. Domain trust
            hostname = urlparse(url).hostname or ""
            if any(d in hostname for d in self.TRUSTED_DOMAINS):
                score += 50

            # 2. Engine trust
            if engine in self.HIGH_TRUST_ENGINES:
                score += 30

            # 3. Content quality
            content_len = len(content)
            if content_len > 200:
                score += 10
            elif content_len > 50:
                score += 5

            scored.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=url,
                    snippet=content,
                    source_engine=engine,
                    trust_score=score,
                    is_trusted=score >= 50,
                )
            )

        return sorted(scored, key=lambda x: x.trust_score, reverse=True)
