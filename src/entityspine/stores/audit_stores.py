"""
Audit Trail Stores - JSON storage for provenance and event tracking.

STDLIB ONLY - NO PYDANTIC.

These stores manage the audit trail data:
- ProvenanceStore: Source tracking (where data came from)
- MergeEventStore: Entity merge history
- SplitEventStore: Entity split history  
- ExplanationStore: Decision explanations
- ResolutionRunStore: Batch execution tracking
- SourceRecordStore: Raw data preservation
- DataQualityStore: Quality check results

v2.3.4: Implements the entity resolution audit trail per ADR-008.
"""

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from entityspine.domain.data_quality import DataQualityResult, DataQualityRule
from entityspine.domain.entity_events import MergeEvent
from entityspine.domain.enums import ProvenanceKind, VendorNamespace
from entityspine.domain.explanation import Explanation, ResolutionRun
from entityspine.domain.provenance import Provenance, SourceRecord
from entityspine.domain.timestamps import from_iso8601, to_iso8601, utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Provenance Store
# =============================================================================


class ProvenanceStore:
    """
    JSON-based store for Provenance records.

    Tracks where data came from for audit trail.

    Example:
        >>> store = ProvenanceStore(Path("data/provenance.json"))
        >>> store.initialize()
        >>> prov = Provenance(
        ...     kind=ProvenanceKind.FILE,
        ...     namespace=VendorNamespace.SEC,
        ...     source_uri="company_tickers.json",
        ... )
        >>> store.save(prov)
    """

    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path
        self._records: dict[str, Provenance] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store, loading from file if exists."""
        if self._initialized:
            return
        if self.json_path and self.json_path.exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"ProvenanceStore initialized with {len(self._records)} records")

    def close(self) -> None:
        """Save and close store."""
        if self.json_path:
            self._save_to_file()
        self._records.clear()
        self._initialized = False

    def save(self, provenance: Provenance) -> None:
        """Save provenance record."""
        self._records[provenance.provenance_id] = provenance

    def get(self, provenance_id: str) -> Provenance | None:
        """Get provenance by ID."""
        return self._records.get(provenance_id)

    def get_by_batch(self, batch_id: str) -> list[Provenance]:
        """Get all provenance records for a batch."""
        return [p for p in self._records.values() if p.batch_id == batch_id]

    def get_by_namespace(self, namespace: VendorNamespace) -> list[Provenance]:
        """Get all provenance records for a namespace."""
        return [p for p in self._records.values() if p.namespace == namespace]

    def count(self) -> int:
        """Get total record count."""
        return len(self._records)

    def all(self) -> Iterator[Provenance]:
        """Iterate all provenance records."""
        yield from self._records.values()

    def _load_from_file(self) -> None:
        """Load records from JSON file."""
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                prov = Provenance(
                    provenance_id=item["provenance_id"],
                    kind=ProvenanceKind(item.get("kind", "file")),
                    namespace=VendorNamespace(item.get("namespace", "internal")),
                    source_uri=item.get("source_uri"),
                    source_hash=item.get("source_hash"),
                    captured_at=from_iso8601(item.get("captured_at")) or utc_now(),
                    captured_by=item.get("captured_by"),
                    file_name=item.get("file_name"),
                    api_endpoint=item.get("api_endpoint"),
                    api_params=item.get("api_params"),
                    batch_id=item.get("batch_id"),
                    notes=item.get("notes"),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._records[prov.provenance_id] = prov
        except Exception as e:
            logger.error(f"Error loading provenance file: {e}")

    def _save_to_file(self) -> None:
        """Save records to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for prov in self._records.values():
                data.append({
                    "provenance_id": prov.provenance_id,
                    "kind": prov.kind.value if hasattr(prov.kind, "value") else str(prov.kind),
                    "namespace": prov.namespace.value if hasattr(prov.namespace, "value") else str(prov.namespace),
                    "source_uri": prov.source_uri,
                    "source_hash": prov.source_hash,
                    "captured_at": to_iso8601(prov.captured_at),
                    "captured_by": prov.captured_by,
                    "file_name": prov.file_name,
                    "api_endpoint": prov.api_endpoint,
                    "api_params": prov.api_params,
                    "batch_id": prov.batch_id,
                    "notes": prov.notes,
                    "created_at": to_iso8601(prov.created_at),
                })
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving provenance file: {e}")


# =============================================================================
# Merge Event Store
# =============================================================================


class MergeEventStore:
    """
    JSON-based store for MergeEvent records.

    Tracks when entities are merged for audit trail and potential reversal.

    Example:
        >>> store = MergeEventStore(Path("data/merge_events.json"))
        >>> store.initialize()
        >>> event = MergeEvent(
        ...     source_entity_id="01HQ...",
        ...     target_entity_id="01HR...",
        ...     reason="same_cik",
        ... )
        >>> store.save(event)
    """

    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path
        self._records: dict[str, MergeEvent] = {}
        self._by_source: dict[str, set[str]] = {}  # source_entity_id -> event_ids
        self._by_target: dict[str, set[str]] = {}  # target_entity_id -> event_ids
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store."""
        if self._initialized:
            return
        if self.json_path and self.json_path.exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"MergeEventStore initialized with {len(self._records)} records")

    def close(self) -> None:
        """Save and close store."""
        if self.json_path:
            self._save_to_file()
        self._records.clear()
        self._by_source.clear()
        self._by_target.clear()
        self._initialized = False

    def save(self, event: MergeEvent) -> None:
        """Save merge event."""
        self._records[event.event_id] = event
        # Update indexes
        self._by_source.setdefault(event.source_entity_id, set()).add(event.event_id)
        self._by_target.setdefault(event.target_entity_id, set()).add(event.event_id)

    def get(self, event_id: str) -> MergeEvent | None:
        """Get merge event by ID."""
        return self._records.get(event_id)

    def get_by_source(self, entity_id: str) -> list[MergeEvent]:
        """Get all merge events where entity was the source (merged away)."""
        event_ids = self._by_source.get(entity_id, set())
        return [self._records[eid] for eid in event_ids if eid in self._records]

    def get_by_target(self, entity_id: str) -> list[MergeEvent]:
        """Get all merge events where entity was the target (canonical)."""
        event_ids = self._by_target.get(entity_id, set())
        return [self._records[eid] for eid in event_ids if eid in self._records]

    def get_by_run(self, run_id: str) -> list[MergeEvent]:
        """Get all merge events from a resolution run."""
        return [e for e in self._records.values() if e.run_id == run_id]

    def count(self) -> int:
        """Get total record count."""
        return len(self._records)

    def all(self) -> Iterator[MergeEvent]:
        """Iterate all merge events."""
        yield from self._records.values()

    def _load_from_file(self) -> None:
        """Load from JSON file."""
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                event = MergeEvent(
                    event_id=item["event_id"],
                    source_entity_id=item["source_entity_id"],
                    target_entity_id=item["target_entity_id"],
                    reason=item.get("reason", "merged"),
                    explanation_id=item.get("explanation_id"),
                    run_id=item.get("run_id"),
                    confidence=item.get("confidence", 1.0),
                    merged_by=item.get("merged_by"),
                    merged_at=from_iso8601(item.get("merged_at")) or utc_now(),
                    source_snapshot=item.get("source_snapshot"),
                    reversible=item.get("reversible", True),
                    reversed=item.get("reversed", False),
                    reversed_at=from_iso8601(item.get("reversed_at")),
                    reversed_by=item.get("reversed_by"),
                    notes=item.get("notes"),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._records[event.event_id] = event
                self._by_source.setdefault(event.source_entity_id, set()).add(event.event_id)
                self._by_target.setdefault(event.target_entity_id, set()).add(event.event_id)
        except Exception as e:
            logger.error(f"Error loading merge events file: {e}")

    def _save_to_file(self) -> None:
        """Save to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for event in self._records.values():
                data.append({
                    "event_id": event.event_id,
                    "source_entity_id": event.source_entity_id,
                    "target_entity_id": event.target_entity_id,
                    "reason": event.reason,
                    "explanation_id": event.explanation_id,
                    "run_id": event.run_id,
                    "confidence": event.confidence,
                    "merged_by": event.merged_by,
                    "merged_at": to_iso8601(event.merged_at),
                    "source_snapshot": event.source_snapshot,
                    "reversible": event.reversible,
                    "reversed": event.reversed,
                    "reversed_at": to_iso8601(event.reversed_at),
                    "reversed_by": event.reversed_by,
                    "notes": event.notes,
                    "created_at": to_iso8601(event.created_at),
                })
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving merge events file: {e}")


# =============================================================================
# Explanation Store
# =============================================================================


class ExplanationStore:
    """
    JSON-based store for Explanation records.

    Tracks reasoning behind resolution decisions.

    Example:
        >>> store = ExplanationStore(Path("data/explanations.json"))
        >>> store.initialize()
        >>> exp = Explanation(
        ...     decision_type="match",
        ...     summary="Matched on CIK",
        ...     confidence=1.0,
        ... )
        >>> store.save(exp)
    """

    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path
        self._records: dict[str, Explanation] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store."""
        if self._initialized:
            return
        if self.json_path and self.json_path.exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"ExplanationStore initialized with {len(self._records)} records")

    def close(self) -> None:
        """Save and close store."""
        if self.json_path:
            self._save_to_file()
        self._records.clear()
        self._initialized = False

    def save(self, explanation: Explanation) -> None:
        """Save explanation record."""
        self._records[explanation.explanation_id] = explanation

    def get(self, explanation_id: str) -> Explanation | None:
        """Get explanation by ID."""
        return self._records.get(explanation_id)

    def count(self) -> int:
        """Get total record count."""
        return len(self._records)

    def all(self) -> Iterator[Explanation]:
        """Iterate all explanations."""
        yield from self._records.values()

    def _load_from_file(self) -> None:
        """Load from JSON file."""
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                exp = Explanation(
                    explanation_id=item["explanation_id"],
                    decision_type=item.get("decision_type", "match"),
                    summary=item.get("summary", ""),
                    details=item.get("details", ""),
                    factors=item.get("factors", {}),
                    confidence=item.get("confidence", 1.0),
                    match_scores=item.get("match_scores", {}),
                    rule_hits=tuple(item.get("rule_hits", [])),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._records[exp.explanation_id] = exp
        except Exception as e:
            logger.error(f"Error loading explanations file: {e}")

    def _save_to_file(self) -> None:
        """Save to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for exp in self._records.values():
                data.append({
                    "explanation_id": exp.explanation_id,
                    "decision_type": exp.decision_type,
                    "summary": exp.summary,
                    "details": exp.details,
                    "factors": exp.factors,
                    "confidence": exp.confidence,
                    "match_scores": exp.match_scores,
                    "rule_hits": list(exp.rule_hits),
                    "created_at": to_iso8601(exp.created_at),
                })
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving explanations file: {e}")


# =============================================================================
# Resolution Run Store
# =============================================================================


class ResolutionRunStore:
    """
    JSON-based store for ResolutionRun records.

    Tracks batch resolution executions.

    Example:
        >>> store = ResolutionRunStore(Path("data/resolution_runs.json"))
        >>> store.initialize()
        >>> run = ResolutionRun(
        ...     input_params={"blocking_keys": ["cik"]},
        ... )
        >>> store.save(run)
    """

    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path
        self._records: dict[str, ResolutionRun] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store."""
        if self._initialized:
            return
        if self.json_path and self.json_path.exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"ResolutionRunStore initialized with {len(self._records)} records")

    def close(self) -> None:
        """Save and close store."""
        if self.json_path:
            self._save_to_file()
        self._records.clear()
        self._initialized = False

    def save(self, run: ResolutionRun) -> None:
        """Save resolution run."""
        self._records[run.run_id] = run

    def get(self, run_id: str) -> ResolutionRun | None:
        """Get resolution run by ID."""
        return self._records.get(run_id)

    def get_recent(self, limit: int = 10) -> list[ResolutionRun]:
        """Get most recent resolution runs."""
        runs = sorted(
            self._records.values(),
            key=lambda r: r.started_at,
            reverse=True,
        )
        return runs[:limit]

    def get_by_status(self, status: str) -> list[ResolutionRun]:
        """Get runs by status."""
        return [r for r in self._records.values() if r.status == status]

    def count(self) -> int:
        """Get total record count."""
        return len(self._records)

    def all(self) -> Iterator[ResolutionRun]:
        """Iterate all runs."""
        yield from self._records.values()

    def _load_from_file(self) -> None:
        """Load from JSON file."""
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                run = ResolutionRun(
                    run_id=item["run_id"],
                    input_params=item.get("input_params", {}),
                    source_record_ids=tuple(item.get("source_record_ids", [])),
                    started_at=from_iso8601(item.get("started_at")) or utc_now(),
                    completed_at=from_iso8601(item.get("completed_at")),
                    stage_metrics=item.get("stage_metrics", {}),
                    entities_created=item.get("entities_created", 0),
                    entities_updated=item.get("entities_updated", 0),
                    entities_merged=item.get("entities_merged", 0),
                    claims_created=item.get("claims_created", 0),
                    claims_superseded=item.get("claims_superseded", 0),
                    avg_confidence=item.get("avg_confidence", 0.0),
                    ambiguous_count=item.get("ambiguous_count", 0),
                    error_count=item.get("error_count", 0),
                    status=item.get("status", "COMPLETED"),
                    error_message=item.get("error_message"),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._records[run.run_id] = run
        except Exception as e:
            logger.error(f"Error loading resolution runs file: {e}")

    def _save_to_file(self) -> None:
        """Save to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for run in self._records.values():
                data.append({
                    "run_id": run.run_id,
                    "input_params": run.input_params,
                    "source_record_ids": list(run.source_record_ids),
                    "started_at": to_iso8601(run.started_at),
                    "completed_at": to_iso8601(run.completed_at),
                    "stage_metrics": run.stage_metrics,
                    "entities_created": run.entities_created,
                    "entities_updated": run.entities_updated,
                    "entities_merged": run.entities_merged,
                    "claims_created": run.claims_created,
                    "claims_superseded": run.claims_superseded,
                    "avg_confidence": run.avg_confidence,
                    "ambiguous_count": run.ambiguous_count,
                    "error_count": run.error_count,
                    "status": run.status,
                    "error_message": run.error_message,
                    "created_at": to_iso8601(run.created_at),
                })
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving resolution runs file: {e}")


# =============================================================================
# Source Record Store
# =============================================================================


class SourceRecordStore:
    """
    JSON-based store for SourceRecord records.

    Preserves raw ingested data before transformation.

    Example:
        >>> store = SourceRecordStore(Path("data/source_records.json"))
        >>> store.initialize()
        >>> record = SourceRecord(
        ...     provenance_id="01HQ...",
        ...     raw_data='{"cik": "320193", "ticker": "AAPL"}',
        ...     record_type="entity",
        ... )
        >>> store.save(record)
    """

    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path
        self._records: dict[str, SourceRecord] = {}
        self._by_provenance: dict[str, set[str]] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store."""
        if self._initialized:
            return
        if self.json_path and self.json_path.exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"SourceRecordStore initialized with {len(self._records)} records")

    def close(self) -> None:
        """Save and close store."""
        if self.json_path:
            self._save_to_file()
        self._records.clear()
        self._by_provenance.clear()
        self._initialized = False

    def save(self, record: SourceRecord) -> None:
        """Save source record."""
        self._records[record.record_id] = record
        if record.provenance_id:
            self._by_provenance.setdefault(record.provenance_id, set()).add(record.record_id)

    def get(self, record_id: str) -> SourceRecord | None:
        """Get source record by ID."""
        return self._records.get(record_id)

    def get_by_provenance(self, provenance_id: str) -> list[SourceRecord]:
        """Get all source records for a provenance."""
        record_ids = self._by_provenance.get(provenance_id, set())
        return [self._records[rid] for rid in record_ids if rid in self._records]

    def get_unprocessed(self) -> list[SourceRecord]:
        """Get all unprocessed source records."""
        return [r for r in self._records.values() if not r.processed]

    def count(self) -> int:
        """Get total record count."""
        return len(self._records)

    def all(self) -> Iterator[SourceRecord]:
        """Iterate all source records."""
        yield from self._records.values()

    def _load_from_file(self) -> None:
        """Load from JSON file."""
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                record = SourceRecord(
                    record_id=item["record_id"],
                    provenance_id=item.get("provenance_id"),
                    raw_data=item.get("raw_data", ""),
                    record_type=item.get("record_type", "unknown"),
                    source_key=item.get("source_key"),
                    processed=item.get("processed", False),
                    processed_at=from_iso8601(item.get("processed_at")),
                    entity_id=item.get("entity_id"),
                    security_id=item.get("security_id"),
                    listing_id=item.get("listing_id"),
                    error_message=item.get("error_message"),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._records[record.record_id] = record
                if record.provenance_id:
                    self._by_provenance.setdefault(record.provenance_id, set()).add(record.record_id)
        except Exception as e:
            logger.error(f"Error loading source records file: {e}")

    def _save_to_file(self) -> None:
        """Save to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for record in self._records.values():
                data.append({
                    "record_id": record.record_id,
                    "provenance_id": record.provenance_id,
                    "raw_data": record.raw_data,
                    "record_type": record.record_type,
                    "source_key": record.source_key,
                    "processed": record.processed,
                    "processed_at": to_iso8601(record.processed_at),
                    "entity_id": record.entity_id,
                    "security_id": record.security_id,
                    "listing_id": record.listing_id,
                    "error_message": record.error_message,
                    "created_at": to_iso8601(record.created_at),
                })
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving source records file: {e}")


# =============================================================================
# Data Quality Store
# =============================================================================


class DataQualityStore:
    """
    JSON-based store for DataQualityRule and DataQualityResult records.

    Manages quality check definitions and results.

    Example:
        >>> store = DataQualityStore(
        ...     rules_path=Path("data/quality_rules.json"),
        ...     results_path=Path("data/quality_results.json"),
        ... )
        >>> store.initialize()
    """

    def __init__(
        self,
        rules_path: Path | None = None,
        results_path: Path | None = None,
    ):
        self.rules_path = rules_path
        self.results_path = results_path
        self._rules: dict[str, DataQualityRule] = {}
        self._results: dict[str, DataQualityResult] = {}
        self._results_by_entity: dict[str, set[str]] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize store."""
        if self._initialized:
            return
        if self.rules_path and self.rules_path.exists():
            self._load_rules()
        if self.results_path and self.results_path.exists():
            self._load_results()
        self._initialized = True
        logger.info(
            f"DataQualityStore initialized with {len(self._rules)} rules, "
            f"{len(self._results)} results"
        )

    def close(self) -> None:
        """Save and close store."""
        if self.rules_path:
            self._save_rules()
        if self.results_path:
            self._save_results()
        self._rules.clear()
        self._results.clear()
        self._results_by_entity.clear()
        self._initialized = False

    # Rule operations
    def save_rule(self, rule: DataQualityRule) -> None:
        """Save quality rule."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> DataQualityRule | None:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_enabled_rules(self) -> list[DataQualityRule]:
        """Get all enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    def all_rules(self) -> Iterator[DataQualityRule]:
        """Iterate all rules."""
        yield from self._rules.values()

    # Result operations
    def save_result(self, result: DataQualityResult) -> None:
        """Save quality result."""
        self._results[result.result_id] = result
        if result.entity_id:
            self._results_by_entity.setdefault(result.entity_id, set()).add(result.result_id)

    def get_result(self, result_id: str) -> DataQualityResult | None:
        """Get result by ID."""
        return self._results.get(result_id)

    def get_results_for_entity(self, entity_id: str) -> list[DataQualityResult]:
        """Get all results for an entity."""
        result_ids = self._results_by_entity.get(entity_id, set())
        return [self._results[rid] for rid in result_ids if rid in self._results]

    def get_failures(self) -> list[DataQualityResult]:
        """Get all failed results."""
        return [r for r in self._results.values() if r.is_failure]

    def get_unresolved_failures(self) -> list[DataQualityResult]:
        """Get unresolved failures needing attention."""
        return [r for r in self._results.values() if r.needs_attention]

    def all_results(self) -> Iterator[DataQualityResult]:
        """Iterate all results."""
        yield from self._results.values()

    def _load_rules(self) -> None:
        """Load rules from JSON file."""
        try:
            with open(self.rules_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                rule = DataQualityRule(
                    rule_id=item["rule_id"],
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    category=item.get("category", "consistency"),
                    severity=item.get("severity", "WARNING"),
                    target_type=item.get("target_type", "entity"),
                    check_expression=item.get("check_expression", ""),
                    enabled=item.get("enabled", True),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                    updated_at=from_iso8601(item.get("updated_at")) or utc_now(),
                )
                self._rules[rule.rule_id] = rule
        except Exception as e:
            logger.error(f"Error loading quality rules file: {e}")

    def _save_rules(self) -> None:
        """Save rules to JSON file."""
        try:
            self.rules_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for rule in self._rules.values():
                data.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category,
                    "severity": rule.severity,
                    "target_type": rule.target_type,
                    "check_expression": rule.check_expression,
                    "enabled": rule.enabled,
                    "created_at": to_iso8601(rule.created_at),
                    "updated_at": to_iso8601(rule.updated_at),
                })
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quality rules file: {e}")

    def _load_results(self) -> None:
        """Load results from JSON file."""
        try:
            with open(self.results_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                result = DataQualityResult(
                    result_id=item["result_id"],
                    rule_id=item.get("rule_id", ""),
                    rule_name=item.get("rule_name", ""),
                    passed=item.get("passed", True),
                    severity=item.get("severity", "INFO"),
                    message=item.get("message", ""),
                    details=item.get("details", {}),
                    entity_id=item.get("entity_id"),
                    claim_id=item.get("claim_id"),
                    security_id=item.get("security_id"),
                    listing_id=item.get("listing_id"),
                    run_id=item.get("run_id"),
                    checked_at=from_iso8601(item.get("checked_at")) or utc_now(),
                    resolved=item.get("resolved", False),
                    resolved_at=from_iso8601(item.get("resolved_at")),
                    resolved_by=item.get("resolved_by"),
                    resolution_notes=item.get("resolution_notes"),
                    created_at=from_iso8601(item.get("created_at")) or utc_now(),
                )
                self._results[result.result_id] = result
                if result.entity_id:
                    self._results_by_entity.setdefault(result.entity_id, set()).add(result.result_id)
        except Exception as e:
            logger.error(f"Error loading quality results file: {e}")

    def _save_results(self) -> None:
        """Save results to JSON file."""
        try:
            self.results_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for result in self._results.values():
                data.append({
                    "result_id": result.result_id,
                    "rule_id": result.rule_id,
                    "rule_name": result.rule_name,
                    "passed": result.passed,
                    "severity": result.severity,
                    "message": result.message,
                    "details": result.details,
                    "entity_id": result.entity_id,
                    "claim_id": result.claim_id,
                    "security_id": result.security_id,
                    "listing_id": result.listing_id,
                    "run_id": result.run_id,
                    "checked_at": to_iso8601(result.checked_at),
                    "resolved": result.resolved,
                    "resolved_at": to_iso8601(result.resolved_at),
                    "resolved_by": result.resolved_by,
                    "resolution_notes": result.resolution_notes,
                    "created_at": to_iso8601(result.created_at),
                })
            with open(self.results_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quality results file: {e}")
