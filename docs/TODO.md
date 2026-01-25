# TODOs - entityspine

> Auto-generated on 2026-02-01 13:53 by `scripts/extract_todos.py`

**Total: 15** (🔴 High: 0, 🟡 Normal: 0, 🟢 Low: 15)

---

## 🟢 Low Priority (15)

- **[NOTE]** Pydantic wrappers available at entityspine.adapters.pydantic (requires [pydantic])
  - 📍 [src\entityspine\adapters\__init__.py:32](src\entityspine\adapters\__init__.py#L32)

- **[NOTE]** ORM layer available at entityspine.adapters.orm (requires [orm])
  - 📍 [src\entityspine\adapters\__init__.py:33](src\entityspine\adapters\__init__.py#L33)

- **[NOTE]** surprise calculation would need consensus observation
  - 📍 [src\entityspine\data\observation_store.py:602](src\entityspine\data\observation_store.py#L602)

- **[NOTE]** Using strings instead of Enum for simplicity and JSON serialization
  - 📍 [src\entityspine\domain\chat.py:31](src\entityspine\domain\chat.py#L31)

- **[NOTE]** dict reference is frozen, contents set once at creation
  - 📍 [src\entityspine\domain\explanation.py:90](src\entityspine\domain\explanation.py#L90)

- **[NOTE]** dict[str, Any] follows existing pattern in ResolutionResult.limits
  - 📍 [src\entityspine\domain\explanation.py:159](src\entityspine\domain\explanation.py#L159)

- **[NOTE]** Reference data has been moved to entityspine.domain.reference_data.markets
  - 📍 [src\entityspine\domain\markets.py:1448](src\entityspine\domain\markets.py#L1448)

- **[NOTE]** Market constants moved to domain.reference_data.markets
  - 📍 [src\entityspine\domain\__init__.py:240](src\entityspine\domain\__init__.py#L240)

- **[NOTE]** Actual FeedSpine API call would go here
  - 📍 [src\entityspine\services\symbology_refresh.py:395](src\entityspine\services\symbology_refresh.py#L395)

- **[NOTE]** GLEIF hosts this at a stable URL, updated daily
  - 📍 [src\entityspine\sources\gleif_mic_lei.py:55](src\entityspine\sources\gleif_mic_lei.py#L55)

- **[NOTE]** country_codes will be empty at this point since XML
  - 📍 [src\entityspine\sources\iso4217.py:747](src\entityspine\sources\iso4217.py#L747)

- **[NOTE]** In production, validate relationship_type against allowed values
  - 📍 [src\entityspine\stores\neo4j_store.py:273](src\entityspine\stores\neo4j_store.py#L273)

- **[NOTE]** This requires the GDS plugin
  - 📍 [src\entityspine\stores\neo4j_store.py:670](src\entityspine\stores\neo4j_store.py#L670)

- **[NOTE]** Would need to add status column to clusters table
  - 📍 [src\entityspine\stores\sqlite\repositories\cluster_repository.py:88](src\entityspine\stores\sqlite\repositories\cluster_repository.py#L88)

- **[NOTE]** Many crypto venues don't have official MICs
  - 📍 [src\entityspine\domain\reference_data\venues.py:510](src\entityspine\domain\reference_data\venues.py#L510)

---

*This file is auto-generated. Run `python scripts/extract_todos.py` to update.*