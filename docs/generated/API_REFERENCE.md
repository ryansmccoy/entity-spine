# API Reference

**Public API Documentation**

*Auto-generated from code annotations on 2026-02-02*

---

## Table of Contents

- [entityspine.adapters.feedspine_adapter](#entityspineadaptersfeedspine_adapter)
- [entityspine.adapters.pydantic.base](#entityspineadapterspydanticbase)
- [entityspine.data.factset.loaders](#entityspinedatafactsetloaders)
- [entityspine.data.observation_store](#entityspinedataobservation_store)
- [entityspine.data.parquet_store](#entityspinedataparquet_store)
- [entityspine.domain.claim](#entityspinedomainclaim)
- [entityspine.domain.data_quality](#entityspinedomaindata_quality)
- [entityspine.domain.entity](#entityspinedomainentity)
- [entityspine.domain.enums.events](#entityspinedomainenumsevents)
- [entityspine.domain.enums.identifiers](#entityspinedomainenumsidentifiers)
- [entityspine.domain.enums.observations](#entityspinedomainenumsobservations)
- [entityspine.domain.explanation](#entityspinedomainexplanation)
- [entityspine.domain.graph](#entityspinedomaingraph)
- [entityspine.domain.listing](#entityspinedomainlisting)
- [entityspine.domain.markets](#entityspinedomainmarkets)
- [entityspine.domain.observation](#entityspinedomainobservation)
- [entityspine.domain.security](#entityspinedomainsecurity)
- [entityspine.domain.workflow](#entityspinedomainworkflow)
- [entityspine.loaders.sec_loader](#entityspineloaderssec_loader)
- [entityspine.services.audit](#entityspineservicesaudit)
- [entityspine.services.fuzzy](#entityspineservicesfuzzy)
- [entityspine.services.graph_service](#entityspineservicesgraph_service)
- [entityspine.services.resolver](#entityspineservicesresolver)
- [entityspine.services.symbology_refresh](#entityspineservicessymbology_refresh)
- [entityspine.sources.gleif](#entityspinesourcesgleif)
- [entityspine.sources.gleif_mic_lei](#entityspinesourcesgleif_mic_lei)
- [entityspine.sources.iso10383](#entityspinesourcesiso10383)
- [entityspine.stores.json_store](#entityspinestoresjson_store)
- [entityspine.stores.sqlite.storage](#entityspinestoressqlitestorage)

---

## entityspine.adapters.feedspine_adapter

### `FeedSpineAdapter`

*Defined in [/app/projects/entityspine/src/entityspine/adapters/feedspine_adapter.py](/app/projects/entityspine/src/entityspine/adapters/feedspine_adapter.py#L78)*

## entityspine.adapters.pydantic.base

### `EntitySpineModel`

*Defined in [/app/projects/entityspine/src/entityspine/adapters/pydantic/base.py](/app/projects/entityspine/src/entityspine/adapters/pydantic/base.py#L18)*

## entityspine.data.factset.loaders

### `FactSetSymbologyLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L149)*

### `FactSetEventsLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L288)*

### `FactSetPeopleLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L420)*

### `FactSetOwnershipLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L527)*

### `FactSetMergersLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L615)*

### `FactSetSupplyChainLoader`

*Defined in [/app/projects/entityspine/src/entityspine/data/factset/loaders.py](/app/projects/entityspine/src/entityspine/data/factset/loaders.py#L749)*

## entityspine.data.observation_store

### `FinancialObservationStore`

*Defined in [/app/projects/entityspine/src/entityspine/data/observation_store.py](/app/projects/entityspine/src/entityspine/data/observation_store.py#L235)*

## entityspine.data.parquet_store

### `ParquetEntityStore`

*Defined in [/app/projects/entityspine/src/entityspine/data/parquet_store.py](/app/projects/entityspine/src/entityspine/data/parquet_store.py#L24)*

## entityspine.domain.claim

### `IdentifierClaim`

*Defined in [/app/projects/entityspine/src/entityspine/domain/claim.py](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

## entityspine.domain.data_quality

### `DataQualityRule`

*Defined in [/app/projects/entityspine/src/entityspine/domain/data_quality.py](/app/projects/entityspine/src/entityspine/domain/data_quality.py#L30)*

### `DataQualityResult`

*Defined in [/app/projects/entityspine/src/entityspine/domain/data_quality.py](/app/projects/entityspine/src/entityspine/domain/data_quality.py#L84)*

## entityspine.domain.entity

### `Entity`

*Defined in [/app/projects/entityspine/src/entityspine/domain/entity.py](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

## entityspine.domain.enums.events

### `EventType`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/events.py](/app/projects/entityspine/src/entityspine/domain/enums/events.py#L10)*

### `DataQualitySeverity`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/events.py](/app/projects/entityspine/src/entityspine/domain/enums/events.py#L181)*

### `RunStatus`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/events.py](/app/projects/entityspine/src/entityspine/domain/enums/events.py#L198)*

### `DecisionType`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/events.py](/app/projects/entityspine/src/entityspine/domain/enums/events.py#L216)*

## entityspine.domain.enums.identifiers

### `IdentifierScheme`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/identifiers.py](/app/projects/entityspine/src/entityspine/domain/enums/identifiers.py#L10)*

### `SanctionStatus`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/identifiers.py](/app/projects/entityspine/src/entityspine/domain/enums/identifiers.py#L93)*

## entityspine.domain.enums.observations

### `PeriodType`

*Defined in [/app/projects/entityspine/src/entityspine/domain/enums/observations.py](/app/projects/entityspine/src/entityspine/domain/enums/observations.py#L229)*

## entityspine.domain.explanation

### `Explanation`

*Defined in [/app/projects/entityspine/src/entityspine/domain/explanation.py](/app/projects/entityspine/src/entityspine/domain/explanation.py#L29)*

### `ResolutionRun`

*Defined in [/app/projects/entityspine/src/entityspine/domain/explanation.py](/app/projects/entityspine/src/entityspine/domain/explanation.py#L111)*

## entityspine.domain.graph

### `Relationship`

*Defined in [/app/projects/entityspine/src/entityspine/domain/graph.py](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

### `Event`

*Defined in [/app/projects/entityspine/src/entityspine/domain/graph.py](/app/projects/entityspine/src/entityspine/domain/graph.py#L1541)*

## entityspine.domain.listing

### `Listing`

*Defined in [/app/projects/entityspine/src/entityspine/domain/listing.py](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

## entityspine.domain.markets

### `BrokerDealer`

*Defined in [/app/projects/entityspine/src/entityspine/domain/markets.py](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

### `Clearinghouse`

*Defined in [/app/projects/entityspine/src/entityspine/domain/markets.py](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*

### `ClearingMembership`

*Defined in [/app/projects/entityspine/src/entityspine/domain/markets.py](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*

### `ExchangeMembership`

*Defined in [/app/projects/entityspine/src/entityspine/domain/markets.py](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*

## entityspine.domain.observation

### `FiscalPeriod`

*Defined in [/app/projects/entityspine/src/entityspine/domain/observation.py](/app/projects/entityspine/src/entityspine/domain/observation.py#L212)*

### `Observation`

*Defined in [/app/projects/entityspine/src/entityspine/domain/observation.py](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

## entityspine.domain.security

### `Security`

*Defined in [/app/projects/entityspine/src/entityspine/domain/security.py](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

## entityspine.domain.workflow

### `ExecutionContext`

*Defined in [/app/projects/entityspine/src/entityspine/domain/workflow.py](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*

### `Ok`

*Defined in [/app/projects/entityspine/src/entityspine/domain/workflow.py](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*

### `Err`

*Defined in [/app/projects/entityspine/src/entityspine/domain/workflow.py](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*

## entityspine.loaders.sec_loader

### `SecDataLoader`

*Defined in [/app/projects/entityspine/src/entityspine/loaders/sec_loader.py](/app/projects/entityspine/src/entityspine/loaders/sec_loader.py#L52)*

## entityspine.services.audit

### `AuditManager`

*Defined in [/app/projects/entityspine/src/entityspine/services/audit.py](/app/projects/entityspine/src/entityspine/services/audit.py#L400)*

## entityspine.services.fuzzy

### `FuzzyMatcher`

*Defined in [/app/projects/entityspine/src/entityspine/services/fuzzy.py](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

## entityspine.services.graph_service

### `GraphService`

*Defined in [/app/projects/entityspine/src/entityspine/services/graph_service.py](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

## entityspine.services.resolver

### `EntityResolver`

*Defined in [/app/projects/entityspine/src/entityspine/services/resolver.py](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

## entityspine.services.symbology_refresh

### `SymbologyRefreshService`

*Defined in [/app/projects/entityspine/src/entityspine/services/symbology_refresh.py](/app/projects/entityspine/src/entityspine/services/symbology_refresh.py#L131)*

## entityspine.sources.gleif

### `GLEIFSource`

*Defined in [/app/projects/entityspine/src/entityspine/sources/gleif.py](/app/projects/entityspine/src/entityspine/sources/gleif.py#L339)*

### `LEIRegistry`

*Defined in [/app/projects/entityspine/src/entityspine/sources/gleif.py](/app/projects/entityspine/src/entityspine/sources/gleif.py#L890)*

## entityspine.sources.gleif_mic_lei

### `GLEIFMICLEISource`

*Defined in [/app/projects/entityspine/src/entityspine/sources/gleif_mic_lei.py](/app/projects/entityspine/src/entityspine/sources/gleif_mic_lei.py#L128)*

## entityspine.sources.iso10383

### `ISO10383Source`

*Defined in [/app/projects/entityspine/src/entityspine/sources/iso10383.py](/app/projects/entityspine/src/entityspine/sources/iso10383.py#L252)*

### `MICRegistry`

*Defined in [/app/projects/entityspine/src/entityspine/sources/iso10383.py](/app/projects/entityspine/src/entityspine/sources/iso10383.py#L601)*

## entityspine.stores.json_store

### `JsonEntityStore`

*Defined in [/app/projects/entityspine/src/entityspine/stores/json_store.py](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

## entityspine.stores.sqlite.storage

### `SqliteStore`

*Defined in [/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*


---

*49 classes across 29 modules*

*Generated by [doc-automation](https://github.com/your-org/py-sec-edgar/tree/main/spine-core/packages/doc-automation)*