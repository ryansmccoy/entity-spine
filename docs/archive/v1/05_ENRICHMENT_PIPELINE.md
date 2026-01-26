# Entity Master - Enrichment Pipeline

Automated enrichment from external data sources.

---

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ENRICHMENT PIPELINE                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   BASE ENTITY                    ENRICHERS                  ENRICHED ENTITY   │
│   ───────────                    ─────────                  ───────────────   │
│                                                                               │
│   ┌─────────────────┐                                                         │
│   │ Entity          │                                                         │
│   │                 │                                                         │
│   │ cik: 320193     │──────┐                                                  │
│   │ name: Apple Inc │      │      ┌──────────────────┐                        │
│   │ ticker: AAPL    │      │      │                  │                        │
│   │                 │      ├─────▶│  SEC Enricher    │──┐                     │
│   │ (no LEI)        │      │      │  (submissions)   │  │                     │
│   │ (no FIGI)       │      │      └──────────────────┘  │                     │
│   │ (no SIC)        │      │                            │                     │
│   └─────────────────┘      │      ┌──────────────────┐  │   ┌──────────────┐  │
│                            │      │                  │  │   │              │  │
│                            ├─────▶│  GLEIF Enricher  │──┼──▶│  Entity      │  │
│                            │      │  (LEI lookup)    │  │   │              │  │
│                            │      └──────────────────┘  │   │  cik: 320193 │  │
│                            │                            │   │  name: Apple │  │
│                            │      ┌──────────────────┐  │   │  ticker: AAPL│  │
│                            │      │                  │  │   │              │  │
│                            ├─────▶│  OpenFIGI        │──┤   │  lei: 549300 │  │
│                            │      │  Enricher        │  │   │  figi: BBG00 │  │
│                            │      └──────────────────┘  │   │  sic: 3571   │  │
│                            │                            │   │              │  │
│                            │      ┌──────────────────┐  │   │  metadata:   │  │
│                            │      │                  │  │   │   state: CA  │  │
│                            └─────▶│  LLM Enricher    │──┘   │   industry:  │  │
│                                   │  (relationships) │      │    Tech HW   │  │
│                                   └──────────────────┘      └──────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Auto-Registration

Enrichers automatically register themselves with Entity Master on startup:

```python
# entity_master/enrichment/registry.py

from abc import ABC, abstractmethod
from typing import ClassVar
import importlib
import pkgutil


class EnricherRegistry:
    """Central registry for enricher plugins."""
    
    _enrichers: dict[str, "BaseEnricher"] = {}
    _discovery_done: bool = False
    
    @classmethod
    def register(cls, enricher: "BaseEnricher"):
        """Register an enricher."""
        cls._enrichers[enricher.enricher_id] = enricher
        print(f"Registered enricher: {enricher.enricher_id}")
    
    @classmethod
    def discover(cls):
        """Auto-discover enrichers from installed packages."""
        if cls._discovery_done:
            return
        
        # Discover built-in enrichers
        from entity_master.enrichment import enrichers
        
        for importer, modname, ispkg in pkgutil.iter_modules(enrichers.__path__):
            module = importlib.import_module(f"entity_master.enrichment.enrichers.{modname}")
            
            # Find enricher classes
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type) and
                    issubclass(obj, BaseEnricher) and
                    obj is not BaseEnricher and
                    hasattr(obj, "enricher_id")
                ):
                    cls.register(obj())
        
        # Discover plugin enrichers (entry points)
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="entity_master.enrichers")
            for ep in eps:
                enricher_class = ep.load()
                cls.register(enricher_class())
        except Exception:
            pass
        
        cls._discovery_done = True
    
    @classmethod
    def get(cls, enricher_id: str) -> "BaseEnricher | None":
        """Get enricher by ID."""
        cls.discover()
        return cls._enrichers.get(enricher_id)
    
    @classmethod
    def all(cls) -> list["BaseEnricher"]:
        """Get all registered enrichers."""
        cls.discover()
        return list(cls._enrichers.values())


class BaseEnricher(ABC):
    """Base class for enrichers."""
    
    # Unique identifier (auto-registered)
    enricher_id: ClassVar[str]
    
    # Display name
    name: ClassVar[str]
    
    # Priority (lower = runs first)
    priority: ClassVar[int] = 100
    
    # What identifier schemes this enricher can use as input
    input_schemes: ClassVar[list[str]]
    
    # What identifier schemes this enricher can add
    output_schemes: ClassVar[list[str]]
    
    # Rate limit (requests per minute)
    rate_limit: ClassVar[int] = 60
    
    def __init_subclass__(cls, **kwargs):
        """Auto-register subclasses."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "enricher_id") and cls.enricher_id:
            # Will be registered when instantiated
            pass
    
    @abstractmethod
    async def can_enrich(self, entity: dict) -> bool:
        """Check if this enricher can enrich the entity."""
        ...
    
    @abstractmethod
    async def enrich(self, entity: dict) -> dict:
        """Enrich the entity, return updated entity dict."""
        ...
```

---

## Built-in Enrichers

### SEC Enricher

```python
# entity_master/enrichment/enrichers/sec.py

from typing import ClassVar
import httpx
from entity_master.enrichment.registry import BaseEnricher


class SECEnricher(BaseEnricher):
    """Enrich from SEC EDGAR submissions API.
    
    Adds:
    - SIC code and description
    - State of incorporation
    - Fiscal year end
    - EIN (if available)
    - All tickers and exchanges
    - Category (filer status)
    """
    
    enricher_id: ClassVar[str] = "sec"
    name: ClassVar[str] = "SEC EDGAR"
    priority: ClassVar[int] = 10  # Run early (free, fast)
    input_schemes: ClassVar[list[str]] = ["cik"]
    output_schemes: ClassVar[list[str]] = ["ticker"]  # Can add tickers
    rate_limit: ClassVar[int] = 10  # SEC asks for <10 req/sec
    
    BASE_URL = "https://data.sec.gov/submissions"
    
    async def can_enrich(self, entity: dict) -> bool:
        """Can enrich if entity has a CIK."""
        return bool(self._get_cik(entity))
    
    async def enrich(self, entity: dict) -> dict:
        """Fetch SEC submission data."""
        cik = self._get_cik(entity)
        if not cik:
            return entity
        
        url = f"{self.BASE_URL}/CIK{cik.zfill(10)}.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": "EntityMaster/1.0 (your@email.com)"},
                timeout=30.0,
            )
            
            if response.status_code != 200:
                return entity
            
            data = response.json()
        
        # Update entity
        entity = entity.copy()
        
        # Add metadata
        entity.setdefault("metadata", {})
        entity["metadata"].update({
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
            "state_of_incorporation": data.get("stateOfIncorporation"),
            "fiscal_year_end": data.get("fiscalYearEnd"),
            "ein": data.get("ein"),
            "category": data.get("category"),
        })
        
        # Add tickers as identifiers
        tickers = data.get("tickers", [])
        exchanges = data.get("exchanges", [])
        
        for ticker, exchange in zip(tickers, exchanges):
            self._add_identifier(entity, "ticker", ticker, exchange=exchange)
        
        return entity
    
    def _get_cik(self, entity: dict) -> str | None:
        """Extract CIK from entity."""
        for ident in entity.get("identifiers", []):
            if ident.get("scheme") == "cik":
                return ident.get("value")
        return None
    
    def _add_identifier(
        self,
        entity: dict,
        scheme: str,
        value: str,
        **kwargs,
    ):
        """Add identifier if not already present."""
        identifiers = entity.setdefault("identifiers", [])
        
        # Check if already exists
        for ident in identifiers:
            if ident.get("scheme") == scheme and ident.get("value") == value:
                return
        
        identifiers.append({
            "scheme": scheme,
            "value": value,
            **kwargs,
        })
```

### GLEIF Enricher

```python
# entity_master/enrichment/enrichers/gleif.py

from typing import ClassVar
import httpx
from entity_master.enrichment.registry import BaseEnricher


class GLEIFEnricher(BaseEnricher):
    """Enrich from GLEIF LEI API.
    
    Adds:
    - LEI
    - Legal jurisdiction
    - Entity status
    - Legal form
    - Addresses
    """
    
    enricher_id: ClassVar[str] = "gleif"
    name: ClassVar[str] = "GLEIF LEI"
    priority: ClassVar[int] = 20  # Run after SEC
    input_schemes: ClassVar[list[str]] = ["lei", "name"]  # Can search by name
    output_schemes: ClassVar[list[str]] = ["lei"]
    rate_limit: ClassVar[int] = 60  # GLEIF is generous
    
    BASE_URL = "https://api.gleif.org/api/v1"
    
    async def can_enrich(self, entity: dict) -> bool:
        """Can enrich if entity has LEI or name."""
        has_lei = any(
            i.get("scheme") == "lei"
            for i in entity.get("identifiers", [])
        )
        has_name = bool(entity.get("primary_name"))
        return has_lei or has_name
    
    async def enrich(self, entity: dict) -> dict:
        """Fetch GLEIF LEI data."""
        entity = entity.copy()
        
        # Try by LEI first
        lei = self._get_identifier(entity, "lei")
        if lei:
            return await self._enrich_by_lei(entity, lei)
        
        # Search by name
        name = entity.get("primary_name")
        if name:
            return await self._enrich_by_name(entity, name)
        
        return entity
    
    async def _enrich_by_lei(self, entity: dict, lei: str) -> dict:
        """Enrich using direct LEI lookup."""
        url = f"{self.BASE_URL}/lei-records/{lei}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            
            if response.status_code != 200:
                return entity
            
            data = response.json()
        
        return self._apply_gleif_data(entity, data["data"])
    
    async def _enrich_by_name(self, entity: dict, name: str) -> dict:
        """Search GLEIF by entity name."""
        url = f"{self.BASE_URL}/lei-records"
        params = {
            "filter[entity.legalName]": name,
            "page[size]": 5,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code != 200:
                return entity
            
            data = response.json()
        
        if not data.get("data"):
            return entity
        
        # Use best match (first result)
        return self._apply_gleif_data(entity, data["data"][0])
    
    def _apply_gleif_data(self, entity: dict, gleif_data: dict) -> dict:
        """Apply GLEIF data to entity."""
        attrs = gleif_data.get("attributes", {})
        lei_data = attrs.get("lei")
        entity_data = attrs.get("entity", {})
        
        # Add LEI identifier
        if lei_data:
            self._add_identifier(entity, "lei", lei_data)
        
        # Add metadata
        entity.setdefault("metadata", {})
        entity["metadata"].update({
            "legal_jurisdiction": entity_data.get("legalJurisdiction"),
            "entity_status": entity_data.get("status"),
            "legal_form": entity_data.get("legalForm", {}).get("id"),
            "category": entity_data.get("category"),
        })
        
        # Add addresses
        legal_address = entity_data.get("legalAddress", {})
        hq_address = entity_data.get("headquartersAddress", {})
        
        entity["metadata"]["legal_address"] = {
            "line1": legal_address.get("addressLines", [""])[0] if legal_address.get("addressLines") else "",
            "city": legal_address.get("city"),
            "region": legal_address.get("region"),
            "postal_code": legal_address.get("postalCode"),
            "country": legal_address.get("country"),
        }
        
        entity["metadata"]["headquarters_address"] = {
            "city": hq_address.get("city"),
            "country": hq_address.get("country"),
        }
        
        return entity
    
    def _get_identifier(self, entity: dict, scheme: str) -> str | None:
        for ident in entity.get("identifiers", []):
            if ident.get("scheme") == scheme:
                return ident.get("value")
        return None
    
    def _add_identifier(self, entity: dict, scheme: str, value: str):
        identifiers = entity.setdefault("identifiers", [])
        for ident in identifiers:
            if ident.get("scheme") == scheme and ident.get("value") == value:
                return
        identifiers.append({"scheme": scheme, "value": value})
```

### OpenFIGI Enricher

```python
# entity_master/enrichment/enrichers/openfigi.py

from typing import ClassVar
import httpx
from entity_master.enrichment.registry import BaseEnricher


class OpenFIGIEnricher(BaseEnricher):
    """Enrich from OpenFIGI API.
    
    Adds:
    - FIGI (Financial Instrument Global Identifier)
    - Composite FIGI
    - Share class FIGI
    - Security type
    - Market sector
    
    Note: OpenFIGI requires mapping jobs, no direct lookup.
    API limits: 25,000 requests/minute (free), 250 jobs/request
    """
    
    enricher_id: ClassVar[str] = "openfigi"
    name: ClassVar[str] = "OpenFIGI"
    priority: ClassVar[int] = 30  # Run after GLEIF
    input_schemes: ClassVar[list[str]] = ["ticker", "isin", "cusip", "sedol"]
    output_schemes: ClassVar[list[str]] = ["figi"]
    rate_limit: ClassVar[int] = 250  # Batch-friendly
    
    BASE_URL = "https://api.openfigi.com/v3/mapping"
    
    # Optional API key for higher limits
    api_key: str | None = None
    
    async def can_enrich(self, entity: dict) -> bool:
        """Can enrich if entity has mappable identifier."""
        schemes = {"ticker", "isin", "cusip", "sedol"}
        return any(
            i.get("scheme") in schemes
            for i in entity.get("identifiers", [])
        )
    
    async def enrich(self, entity: dict) -> dict:
        """Fetch FIGI mapping."""
        entity = entity.copy()
        
        # Build mapping request
        jobs = self._build_jobs(entity)
        if not jobs:
            return entity
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-OPENFIGI-APIKEY"] = self.api_key
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.BASE_URL,
                json=jobs,
                headers=headers,
                timeout=30.0,
            )
            
            if response.status_code != 200:
                return entity
            
            results = response.json()
        
        # Apply results
        for result in results:
            if "data" in result:
                entity = self._apply_figi_data(entity, result["data"])
                break  # Use first successful result
        
        return entity
    
    def _build_jobs(self, entity: dict) -> list[dict]:
        """Build OpenFIGI mapping jobs."""
        jobs = []
        
        for ident in entity.get("identifiers", []):
            scheme = ident.get("scheme")
            value = ident.get("value")
            
            if scheme == "ticker":
                exchange = ident.get("exchange", "")
                mic = self._exchange_to_mic(exchange)
                jobs.append({
                    "idType": "TICKER",
                    "idValue": value,
                    "exchCode": mic if mic else None,
                })
            
            elif scheme == "isin":
                jobs.append({
                    "idType": "ID_ISIN",
                    "idValue": value,
                })
            
            elif scheme == "cusip":
                jobs.append({
                    "idType": "ID_CUSIP",
                    "idValue": value,
                })
            
            elif scheme == "sedol":
                jobs.append({
                    "idType": "ID_SEDOL",
                    "idValue": value,
                })
        
        # Filter None values
        return [{k: v for k, v in job.items() if v is not None} for job in jobs]
    
    def _exchange_to_mic(self, exchange: str) -> str | None:
        """Convert exchange name to MIC code."""
        mapping = {
            "NYSE": "XNYS",
            "NASDAQ": "XNAS",
            "AMEX": "XASE",
            "BATS": "BATS",
            "ARCA": "ARCX",
        }
        return mapping.get(exchange.upper()) if exchange else None
    
    def _apply_figi_data(self, entity: dict, figi_data: list[dict]) -> dict:
        """Apply FIGI data to entity."""
        if not figi_data:
            return entity
        
        # Get best match (usually first)
        best = figi_data[0]
        
        # Add FIGI identifier
        figi = best.get("figi")
        if figi:
            self._add_identifier(entity, "figi", figi)
        
        composite_figi = best.get("compositeFIGI")
        if composite_figi and composite_figi != figi:
            self._add_identifier(entity, "composite_figi", composite_figi)
        
        share_class_figi = best.get("shareClassFIGI")
        if share_class_figi and share_class_figi != figi:
            self._add_identifier(entity, "share_class_figi", share_class_figi)
        
        # Add metadata
        entity.setdefault("metadata", {})
        entity["metadata"].update({
            "security_type": best.get("securityType"),
            "security_type2": best.get("securityType2"),
            "market_sector": best.get("marketSector"),
        })
        
        return entity
    
    def _add_identifier(self, entity: dict, scheme: str, value: str):
        identifiers = entity.setdefault("identifiers", [])
        for ident in identifiers:
            if ident.get("scheme") == scheme and ident.get("value") == value:
                return
        identifiers.append({"scheme": scheme, "value": value})
```

---

## LLM Enrichment (Tier 5)

### Relationship Extraction

```python
# entity_master/enrichment/enrichers/llm_relationships.py

from typing import ClassVar
from entity_master.enrichment.registry import BaseEnricher


class LLMRelationshipEnricher(BaseEnricher):
    """Extract relationships using LLM analysis.
    
    Sources:
    - SEC filings (10-K risk factors, MD&A)
    - News articles
    - Press releases
    
    Extracts:
    - Supplier relationships
    - Customer relationships
    - Competitor mentions
    - Partnership announcements
    """
    
    enricher_id: ClassVar[str] = "llm_relationships"
    name: ClassVar[str] = "LLM Relationship Extraction"
    priority: ClassVar[int] = 100  # Run last (expensive)
    input_schemes: ClassVar[list[str]] = ["cik"]  # Need filings
    output_schemes: ClassVar[list[str]] = []  # Outputs relationships, not identifiers
    rate_limit: ClassVar[int] = 10  # API cost concerns
    
    def __init__(self, llm_client=None, model: str = "gpt-4o-mini"):
        self.llm = llm_client
        self.model = model
    
    async def can_enrich(self, entity: dict) -> bool:
        """Can enrich if entity has CIK (for filing analysis)."""
        return any(
            i.get("scheme") == "cik"
            for i in entity.get("identifiers", [])
        )
    
    async def enrich(self, entity: dict) -> dict:
        """Extract relationships from filings."""
        cik = self._get_identifier(entity, "cik")
        if not cik:
            return entity
        
        entity = entity.copy()
        
        # Get latest 10-K text (simplified - actual would fetch from py-sec-edgar)
        filing_text = await self._get_10k_text(cik)
        if not filing_text:
            return entity
        
        # Extract relationships using LLM
        relationships = await self._extract_relationships(entity, filing_text)
        
        # Store relationships
        entity.setdefault("extracted_relationships", [])
        entity["extracted_relationships"].extend(relationships)
        
        return entity
    
    async def _extract_relationships(
        self,
        entity: dict,
        filing_text: str,
    ) -> list[dict]:
        """Extract relationships using LLM."""
        
        prompt = f"""Analyze this SEC 10-K filing excerpt and extract business relationships.

Company: {entity.get('primary_name', 'Unknown')}

Filing Text:
{filing_text[:8000]}  # Truncate for API limits

Extract relationships in these categories:
1. SUPPLIERS - Companies that supply materials/services to this company
2. CUSTOMERS - Companies that buy from this company
3. COMPETITORS - Direct competitors mentioned
4. PARTNERS - Strategic partners or joint ventures

For each relationship, provide:
- Company name
- Relationship type
- Confidence (0-1)
- Evidence quote

Format as JSON array:
[
  {{
    "target_name": "Company Name",
    "relationship_type": "SUPPLIER_OF",
    "confidence": 0.85,
    "evidence": "Quote from filing..."
  }}
]"""

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        
        import json
        relationships = json.loads(response.choices[0].message.content)
        
        # Add source metadata
        for rel in relationships:
            rel["source"] = "llm_10k_analysis"
            rel["enricher"] = self.enricher_id
        
        return relationships
    
    async def _get_10k_text(self, cik: str) -> str | None:
        """Get 10-K filing text (stub - integrate with py-sec-edgar)."""
        # In real implementation:
        # from py_sec_edgar import SECClient
        # client = SECClient()
        # filing = client.get_latest_filing(cik=cik, form_type="10-K")
        # return filing.get_text()
        return None
    
    def _get_identifier(self, entity: dict, scheme: str) -> str | None:
        for ident in entity.get("identifiers", []):
            if ident.get("scheme") == scheme:
                return ident.get("value")
        return None


class LLMEntityExtractor(BaseEnricher):
    """Extract entity mentions from text using LLM.
    
    Use cases:
    - Extract all company mentions from a filing
    - Identify people mentioned (executives, directors)
    - Extract locations and dates
    """
    
    enricher_id: ClassVar[str] = "llm_entity_extraction"
    name: ClassVar[str] = "LLM Entity Extraction"
    priority: ClassVar[int] = 100
    input_schemes: ClassVar[list[str]] = []  # Works on text, not identifiers
    output_schemes: ClassVar[list[str]] = []
    rate_limit: ClassVar[int] = 10
    
    async def extract_entities(self, text: str) -> list[dict]:
        """Extract all entity mentions from text."""
        prompt = f"""Extract all company, person, and location mentions from this text.

Text:
{text[:8000]}

For each entity, provide:
- name: The entity name as mentioned
- type: COMPANY, PERSON, or LOCATION
- context: Brief context of the mention
- start_char: Character position where mention starts (approximate)

Format as JSON array."""

        # ... LLM call similar to above
        pass
```

### Entity Resolution with Embeddings

```python
# entity_master/enrichment/enrichers/llm_resolution.py

from typing import ClassVar
import numpy as np
from entity_master.enrichment.registry import BaseEnricher


class EmbeddingMatcher(BaseEnricher):
    """Match entities using embedding similarity.
    
    Used for:
    - Fuzzy name matching
    - Finding entity mentions in text
    - Cross-language entity resolution
    """
    
    enricher_id: ClassVar[str] = "embedding_matcher"
    name: ClassVar[str] = "Embedding-based Entity Matching"
    priority: ClassVar[int] = 50
    input_schemes: ClassVar[list[str]] = []
    output_schemes: ClassVar[list[str]] = []
    rate_limit: ClassVar[int] = 100
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.model = embedding_model
        self._embedding_cache = {}
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text."""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        # Call embedding API
        response = await self.llm.embeddings.create(
            model=self.model,
            input=text,
        )
        
        embedding = np.array(response.data[0].embedding)
        self._embedding_cache[text] = embedding
        return embedding
    
    async def find_matches(
        self,
        query: str,
        candidates: list[dict],
        threshold: float = 0.85,
    ) -> list[tuple[dict, float]]:
        """Find matching entities by embedding similarity."""
        query_embedding = await self.get_embedding(query)
        
        matches = []
        for candidate in candidates:
            name = candidate.get("primary_name", "")
            cand_embedding = await self.get_embedding(name)
            
            # Cosine similarity
            similarity = np.dot(query_embedding, cand_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(cand_embedding)
            )
            
            if similarity >= threshold:
                matches.append((candidate, float(similarity)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
```

---

## Enrichment Pipeline

```python
# entity_master/enrichment/pipeline.py

from datetime import datetime, timedelta
from entity_master.enrichment.registry import EnricherRegistry


class EnrichmentPipeline:
    """Orchestrates the enrichment process."""
    
    def __init__(
        self,
        entity_master,
        enrichers: list[str] = None,
        cache_ttl: timedelta = timedelta(days=30),
    ):
        self.em = entity_master
        self.enricher_ids = enrichers or ["sec", "gleif", "openfigi"]
        self.cache_ttl = cache_ttl
    
    async def enrich(
        self,
        entity: dict,
        force: bool = False,
        enrichers: list[str] = None,
    ) -> dict:
        """Run enrichment pipeline on entity.
        
        Args:
            entity: Entity to enrich
            force: Re-enrich even if cached
            enrichers: Specific enrichers to run (or all)
        """
        enricher_ids = enrichers or self.enricher_ids
        
        # Check cache
        if not force:
            cached = await self._check_cache(entity)
            if cached:
                return cached
        
        # Get enrichers sorted by priority
        all_enrichers = EnricherRegistry.all()
        selected = [
            e for e in all_enrichers
            if e.enricher_id in enricher_ids
        ]
        selected.sort(key=lambda e: e.priority)
        
        # Run enrichers in order
        for enricher in selected:
            if await enricher.can_enrich(entity):
                try:
                    entity = await enricher.enrich(entity)
                    entity["_last_enriched"] = {
                        enricher.enricher_id: datetime.utcnow().isoformat()
                    }
                except Exception as e:
                    # Log error but continue
                    print(f"Enricher {enricher.enricher_id} failed: {e}")
        
        # Update cache
        await self._update_cache(entity)
        
        return entity
    
    async def enrich_batch(
        self,
        entities: list[dict],
        concurrency: int = 10,
    ) -> list[dict]:
        """Enrich multiple entities with concurrency control."""
        import asyncio
        from asyncio import Semaphore
        
        sem = Semaphore(concurrency)
        
        async def enrich_one(entity):
            async with sem:
                return await self.enrich(entity)
        
        return await asyncio.gather(*[
            enrich_one(e) for e in entities
        ])
    
    async def _check_cache(self, entity: dict) -> dict | None:
        """Check if entity was recently enriched."""
        last_enriched = entity.get("_last_enriched", {})
        
        for enricher_id in self.enricher_ids:
            timestamp = last_enriched.get(enricher_id)
            if not timestamp:
                return None  # Not enriched by this enricher
            
            enriched_at = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - enriched_at > self.cache_ttl:
                return None  # Cache expired
        
        return entity  # All enrichers cached
    
    async def _update_cache(self, entity: dict):
        """Store enriched entity."""
        # Actual storage depends on tier
        await self.em.storage.update(entity)
```

---

## CLI Commands

```bash
# Enrich single entity
entity-master enrich AAPL
entity-master enrich "Apple Inc" --enrichers sec,gleif,openfigi

# Batch enrich
entity-master enrich-batch --input entities.json --output enriched.json

# Force re-enrich
entity-master enrich AAPL --force

# Show available enrichers
entity-master enrichers list

# Check enrichment status
entity-master enrichers status AAPL
```

---

## Configuration

```yaml
# entity_master.yaml

enrichment:
  # Default enrichers to run
  default_enrichers:
    - sec
    - gleif
    - openfigi
  
  # Cache settings
  cache_ttl_days: 30
  
  # Enricher-specific config
  enrichers:
    sec:
      enabled: true
      user_agent: "EntityMaster/1.0 (your@email.com)"
    
    gleif:
      enabled: true
    
    openfigi:
      enabled: true
      api_key: ${OPENFIGI_API_KEY}  # Optional
    
    llm_relationships:
      enabled: false  # Tier 5 only
      model: "gpt-4o-mini"
      api_key: ${OPENAI_API_KEY}
    
    embedding_matcher:
      enabled: false  # Tier 5 only
      model: "text-embedding-3-small"
  
  # Rate limiting
  global_rate_limit: 100  # Requests per minute across all enrichers
```
