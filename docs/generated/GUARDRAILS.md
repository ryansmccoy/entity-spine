# GUARDRAILS

**What NOT to Do - Anti-patterns and Constraints**

*Auto-generated from code annotations on 2026-02-02*

---

> These guardrails help prevent common mistakes and enforce best practices.
> Each guardrail includes the anti-pattern to avoid and the correct approach.


## IdentifierClaim

### ❌ Do NOT put identifiers directly on Entity/Security/Listing

✅ **Instead:** Use IdentifierClaim with appropriate target_id

*From [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

### ❌ Do NOT use entity_id for security-scoped schemes (CUSIP, ISIN)

✅ **Instead:** Use security_id for security identifiers

*From [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

### ❌ Do NOT ignore temporal validity for ticker lookups

✅ **Instead:** Check valid_from/valid_to for point-in-time resolution

*From [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

### ❌ Do NOT assume confidence=1.0 for all sources

✅ **Instead:** Assign appropriate confidence by source reliability

*From [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

## Entity

### ❌ Do NOT store CIK, LEI, or EIN on Entity

✅ **Instead:** Use IdentifierClaim with entity_id reference

*From [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

### ❌ Do NOT store ticker symbols on Entity

✅ **Instead:** Use Listing for exchange-specific tickers

*From [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

### ❌ Do NOT delete merged entities

✅ **Instead:** Set redirect_to and status=MERGED

*From [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

## Relationship

### ❌ Do NOT use Relationship for entity→entity links

✅ **Instead:** Use EntityRelationship for cleaner entity graphs

*From [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

### ❌ Do NOT ignore evidence pointers for important relationships

✅ **Instead:** Link to filing_id and extract evidence_snippet

*From [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

### ❌ Do NOT store large text in evidence_snippet

✅ **Instead:** Use evidence_excerpt_hash for full text lookup

*From [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

## Listing

### ❌ Do NOT put ticker on Entity

✅ **Instead:** Use Listing with security_id reference

*From [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

### ❌ Do NOT put ticker on Security

✅ **Instead:** Use Listing (tickers are exchange-specific)

*From [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

### ❌ Do NOT ignore MIC for exchange identification

✅ **Instead:** Use ISO 10383 MIC (XNAS, XNYS, XLON) for unambiguous ID

*From [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

### ❌ Do NOT delete old listings on ticker change

✅ **Instead:** Set end_date on old, create new with start_date

*From [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

## BrokerDealer

### ❌ Do NOT confuse BrokerDealerStatus with MembershipStatus

✅ **Instead:** MembershipStatus = exchange membership (SUSPENDED, REVOKED)

*From [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

### ❌ Do NOT use this model for investment advisers

**Why this is bad:** - CRD validated to numeric format (leading zeros allowed)

✅ **Instead:** BrokerDealers execute trades; IAs provide advice (different regs)

*From [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

## Clearinghouse

### ❌ Do NOT confuse ClearingStatus with MembershipStatus

**Why this is bad:** - SIFMU designation has regulatory implications

✅ **Instead:** Systemically important clearinghouses face enhanced supervision

*From [`Clearinghouse`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*

## ClearingMembership

### ❌ Do NOT confuse MembershipStatus with ClearingStatus

**Why this is bad:** - Correspondent clearing requires clearing_firm_id on BrokerDealer

✅ **Instead:** ClearingStatus = the clearinghouse's overall status

*From [`ClearingMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*

## ExchangeMembership

### ❌ Do NOT confuse MembershipStatus with BrokerDealerStatus

**Why this is bad:** - MPID (member_code) is exchange-specific, not globally unique

✅ **Instead:** BrokerDealerStatus = the firm's overall regulatory status

*From [`ExchangeMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*

## Observation

### ❌ Do NOT store observation without entity_id

✅ **Instead:** Entity reference is required

*From [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

### ❌ Do NOT conflate period, as_of, and captured_at

✅ **Instead:** Use each for its intended purpose

*From [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

### ❌ Do NOT destructively update observations

✅ **Instead:** Create new observation with supersedes_id

*From [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

### ❌ Do NOT rely on is_primary flag for authoritative value

✅ **Instead:** Use supersession chain (superseded_by_id=None)

*From [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

## Security

### ❌ Do NOT store ISIN, CUSIP, SEDOL, FIGI on Security

✅ **Instead:** Use IdentifierClaim with security_id reference

*From [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

### ❌ Do NOT store ticker on Security

✅ **Instead:** Use Listing for exchange-specific tickers

*From [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

### ❌ Do NOT create Security without entity_id

✅ **Instead:** Entity relationship is required - every security has an issuer

*From [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

## ExecutionContext

### ❌ Do NOT reuse execution_id across different runs

✅ **Instead:** Create new context with new_execution_context()

*From [`ExecutionContext`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*

### ❌ Do NOT modify metadata in place

✅ **Instead:** Use with_metadata() to create new context

*From [`ExecutionContext`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*

## Ok

### ❌ Do NOT catch exceptions to return Ok

✅ **Instead:** Use try_result() helper function

*From [`Ok`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*

### ❌ Do NOT call unwrap() without checking is_ok()

✅ **Instead:** Use unwrap_or() or pattern match

*From [`Ok`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*

## Err

### ❌ Do NOT swallow errors silently with unwrap_or

✅ **Instead:** Log or aggregate errors before providing defaults

*From [`Err`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*

### ❌ Do NOT create Err with non-Exception types

✅ **Instead:** Wrap strings in ValueError("message")

*From [`Err`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*

## FuzzyMatcher

### ❌ Do NOT use min_score < 0.5 for production

✅ **Instead:** Use 0.6+ to avoid false positives

*From [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

### ❌ Do NOT skip normalization for company names

✅ **Instead:** Always normalize=True (default)

*From [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

### ❌ Do NOT assume match_many returns all candidates

✅ **Instead:** Only returns candidates above threshold

*From [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

## GraphService

### ❌ Do NOT traverse without max_depth limit on dense graphs

✅ **Instead:** Always set max_depth to prevent runaway queries

*From [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

### ❌ Do NOT ignore is_current checks for temporal accuracy

✅ **Instead:** Use as_of parameter for point-in-time queries

*From [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

### ❌ Do NOT expect BFS to find shortest path in weighted graphs

✅ **Instead:** BFS finds shortest hop count, not weighted distance

*From [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

## EntityResolver

### ❌ Do NOT create new resolver for each query

✅ **Instead:** Reuse resolver instance (stateless after init)

*From [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

### ❌ Do NOT ignore confidence score for fuzzy matches

✅ **Instead:** Check confidence threshold for your use case

*From [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

### ❌ Do NOT assume ticker is unique without MIC

✅ **Instead:** Use MIC for disambiguation or accept multiple candidates

*From [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

## JsonEntityStore

### ❌ Do NOT use JsonEntityStore for >50K entities

✅ **Instead:** Use SqliteStore (T1) for larger datasets

*From [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

### ❌ Do NOT expect as_of queries to work

✅ **Instead:** Use SqliteStore+ for temporal queries

*From [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

### ❌ Do NOT use for concurrent writes

✅ **Instead:** JsonEntityStore is single-writer safe only

*From [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

## SqliteStore

### ❌ Do NOT use SqliteStore for >500K entities

✅ **Instead:** Use DuckDB (T2) or PostgreSQL (T3)

*From [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*

### ❌ Do NOT expect as_of queries to work

✅ **Instead:** Use T2/T3 for temporal queries

*From [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*

### ❌ Do NOT use for concurrent writes

✅ **Instead:** SQLite is single-writer; use connection pooling

*From [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*

### ❌ Do NOT import from old path

✅ **Instead:** from entityspine.stores.sqlite import SqliteStore

*From [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*


---

*48 guardrails documented*

*Generated by [doc-automation](https://github.com/your-org/py-sec-edgar/tree/main/spine-core/packages/doc-automation)*