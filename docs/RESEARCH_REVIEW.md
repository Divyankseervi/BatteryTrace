# Research and repository review (checked 26 October 2026)

This note records prior art that informed BatteryTrace. It is not a claim that BatteryTrace is novel as a whole. BatteryTrace is an educational, locally run prototype and does not claim regulatory compliance.

## Research papers

1. Berger, K., Schöggl, J.-P. and Baumgartner, R. J. (2022), “Digital battery passports to enable circular and sustainable value chains: Conceptualization and use cases,” *Journal of Cleaner Production*, 353, 131492. DOI: https://doi.org/10.1016/j.jclepro.2022.131492
   - Relevance: battery-passport concept and lifecycle use cases. This means a general “battery passport dashboard” is not itself a novel research claim.

2. “A Standardized Data Model for the Battery Passport: Paving the Way for Sustainable Battery Management” (2024), *Procedia CIRP*, 122, 103–108. DOI: https://doi.org/10.1016/j.procir.2024.01.014
   - Relevance: standardized passport data and hierarchical information structures. BatteryTrace therefore makes its data entities and relationships explicit rather than presenting only UI screens.

3. “End of life focused data model for a digital battery passport” (2024), *Procedia CIRP*, 122, 277–281. DOI: https://doi.org/10.1016/j.procir.2024.01.040
   - Relevance: recycling information needs, dynamic data such as state of health, and data gaps in end-of-life operations. BatteryTrace's sample is narrower and does not claim to calculate a battery's real state of health.

4. Tolcha, Y. K., Park, G. and Kim, D. (2025), “Building Digital Product Passports: EPCIS 2.0 Meets Knowledge Graphs,” IEEE International Conference on RFID 2025. DOI: https://doi.org/10.1109/RFID64926.2025.11015538
   - Relevance: graph representation and traceability events have prior art. BatteryTrace must not claim that graph-based DPPs are a new idea. Its proposed student extension is a reproducible comparison of integrity rules and lineage-query correctness under defined workloads.

5. “Using composable NFTs and blockchain for the creation of EV battery digital passports with sustainability and traceability features” (2025), *Digital Chemical Engineering*. ScienceDirect record: https://www.sciencedirect.com/science/article/pii/S2666188825004125
   - Relevance: decentralized/blockchain battery passport architectures already exist. BatteryTrace deliberately uses a conventional relational database as its main teaching implementation instead of adding blockchain without a measured need.

6. “Bridging digital and green transitions: a literature review of digital product passport systems” (2026), *Renewable and Sustainable Energy Reviews*, 228, 116600. DOI: https://doi.org/10.1016/j.rser.2025.116600
   - Relevance: broad review of 186 DPP publications; supports treating knowledge graphs, blockchain, interoperability and layered access as existing research areas, not original claims by this project.

## GitHub and standards repositories reviewed

1. **Eclipse Tractus-X Digital Product Pass (DPP)**: https://github.com/eclipse-tractusx/digital-product-pass
   - Reference implementation for the Catena-X EcoPass KIT in the automotive dataspace. Demonstrates sovereign peer-to-peer data querying using Eclipse Dataspace Connectors (EDCs) and physical QR-code resolution.
2. **Eclipse Tractus-X Item Relationship Service (IRS)**: https://github.com/eclipse-tractusx/item-relationship-service
   - Open-source recursive graph traversal across sovereign supply chain tiers for multi-level Bills of Materials (BOM) and traceability. Confirms that recursive lineage traversal is central to industrial automotive architectures.
3. **Eclipse Tractus-X Semantic Models**: https://github.com/eclipse-tractusx/sldt-semantic-models
   - Standardized aspect models (BAMM / SAMM) for digital battery passports, carbon footprints, and component composition.
4. **Battery Pass Consortium Data Model**: https://thebatterypass.eu/
   - Co-funded by the German Federal Ministry for Economic Affairs and Climate Action (BMWK); defines a comprehensive 90+ attribute specification across general battery data, material composition, circularity, carbon footprint, and performance/durability.
5. **OpenEPCIS**: https://github.com/openepcis / https://github.com/openepcis/epcis-repository-ce
   - Open source GS1 EPCIS 2.0 repository providing event-based supply chain visibility across object, transformation, and aggregation events.
6. **OpenDPP**: https://github.com/0xNadr/OpenDPP
   - Reference implementation of digital product passports leveraging GS1 Digital Link and W3C verifiable credentials.
7. **Global Battery Alliance (GBA)**: https://www.globalbattery.org/battery-passport/
   - Multi-stakeholder consortium establishing standardized GHG calculation rulebooks, human rights benchmarks, and child labor indices for global battery passports.

## Global policy and legislative landscape (2024–2027)

Governments worldwide are establishing mandatory legal frameworks for EV battery lifecycle tracking, material provenance, and circularity:

### 1. European Union — Regulation (EU) 2023/1542
* **Mandatory Battery Passport**: Effective **18 February 2027** for all electric vehicle (EV) batteries, light means of transport (LMT) batteries, and industrial batteries above 2 kWh placed on the EU market.
* **Passport Succession (Article 77(7))**: When a battery undergoes preparation for reuse, repurposing, or remanufacturing, a *new* battery passport must be issued, linked to the predecessor passport(s).
* **Passport Termination (Article 77(8))**: The battery passport ceases to exist after the battery has been recycled.
* **Carbon Footprint Declarations (Article 7)**: Mandatory lifecycle carbon footprint declaration (2025), carbon footprint performance classes (2026), and maximum lifecycle carbon footprint thresholds (2028).
* **Recycled Content Targets (Article 8)**: Mandatory documentation of active materials recovered from waste: initial documentation required, rising to minimum mandatory targets by 2031 (16% Co, 85% Pb, 6% Li, 6% Ni) and 2036 (26% Co, 85% Pb, 12% Li, 15% Ni).
* **State of Health Access (Article 14)**: Real-time and historical BMS data (capacity fade, internal resistance, cycle count) must be accessible to operators and recyclers to determine remaining value.

### 2. United States — Inflation Reduction Act (IRA Section 30D) & FEOC
* **Critical Minerals & Sourcing Requirements**: To qualify for the $7,500 clean vehicle consumer tax credit, an escalating percentage of critical minerals (lithium, nickel, cobalt, graphite, manganese) must be extracted or processed in the US or an FTA partner nation, or recycled in North America.
* **Foreign Entity of Concern (FEOC) Exclusion**: Strict supply chain tracing rules that disqualify any battery containing components (effective 2024) or applicable critical minerals (effective 2025) extracted, processed, or recycled by a foreign entity of concern (PRC, Russia, Iran, DPRK).
* **Traceability Requirement**: OEMs must verify provenance through 4+ tiers of suppliers down to extraction facilities, requiring recursive graph genealogy queries identical to BatteryTrace's recall engine.

### 3. India — Ministry of Environment, Forest & Climate Change (MoEFCC) & NITI Aayog
* **Battery Waste Management (BWM) Rules, 2022**:
  - Imposes mandatory **Extended Producer Responsibility (EPR)** on EV battery manufacturers, assemblers, and vehicle OEMs.
  - Mandatory registration and reporting on the Central Pollution Control Board (CPCB) online EPR portal (`eprbattery.cpcb.gov.in`).
  - Strict recovery targets for critical materials from waste batteries (70% recovery by 2024-25, 80% by 2026-27, 90% by 2028-29) and EPR credit trading between recyclers and producers.
  - Mandatory QR-code labelling on battery packs linking to chemical composition and manufacturing origin.
* **NITI Aayog Battery Swapping Policy**:
  - Mandates a **Unique Identification Number (UIN)** assigned at the manufacturing stage for all swappable battery packs.
  - Requires standardized IoT telemetry, state-of-health logging across swap stations, and interoperable tracking across multiple fleet operators.
* **Production Linked Incentive (PLI) for Advanced Chemistry Cell (ACC)**:
  - 50 GWh domestic manufacturing initiative requiring minimum 60% Domestic Value Addition (DVA) within 5 years, necessitating verified supply chain records for all constituent modules and cells.

## Mapping global regulations to DBMS architectural patterns

| Real-World Policy Requirement | DBMS Technical Challenge | How BatteryTrace Solves It |
|---|---|---|
| **EU Art. 77(7) Passport Chaining** | Linking new passport to predecessor without accidental cycles or cross-asset errors | Trigger `trg_passport_chain` enforces same asset, strictly earlier version; partial unique index enforces at most one `ACTIVE` passport |
| **EU Art. 77(8) Recycling Termination** | Passport and links must close atomically upon recycling | Atomic transaction in `services.record_event` commits `RECYCLED` event, closes passport, closes open links, and trigger `trg_asset_terminal` blocks further status mutations |
| **US IRA / FEOC Batch Tracing** | Tracing multi-tier suppliers from raw batch to finished vehicle | Cycle-safe recursive CTE in `recall.py` (`WITH RECURSIVE`) traverses DAG of `AssetRelationship` rows with batch code filtering |
| **India BWMR EPR Custody Transfers** | Transferring components between owner, refurbisher, and recycler with exact handover dates | Half-open intervals `[valid_from, valid_to)` in `AssetRelationship`, protected by triggers `trg_rel_overlap_ins` and `trg_rel_overlap_upd` |
| **EU Art. 14 / AIS-156 Health Diagnostics** | Preserving repeated State of Health (SoH %) and cycle counts over time without overwrite | Normalized `TestResult` table (`1-N` with `Asset`) with composite index `idx_test_asset_time` supporting fast time-series queries |
| **Tamper-Evident Auditability** | Guaranteeing event logs were not secretly modified or reordered after recording | Append-only SHA-256 hash-chained event ledger (`prev_hash` $\rightarrow$ `event_hash`) with triggers blocking `UPDATE` and `DELETE` |

## What was borrowed as engineering guidance (not copied as code)

- Model lifecycle as timestamped events rather than a single mutable description.
- Keep component identity separate from its relationships and passport versions.
- Treat data standards and exchange formats as interoperability concerns.
- Do not store confidential operational evidence in a public ledger merely because the project concerns traceability.
- Separate what the application detects from what it can actually prove. A rule-based warning is not proof of fraud, physical truth or legal non-compliance.

## Proposed defensible student contribution

A reasonable next research increment is to generate the same synthetic battery hierarchy and lifecycle event dataset for SQLite/PostgreSQL and Neo4j, then compare (a) correctness/completeness of downstream recall queries, (b) ability to reject invalid component assignments, (c) p50/p95 latency across fixed dataset sizes, and (d) behaviour under concurrent writes. This is a proposed experiment, not a result already measured in BatteryTrace. A fair comparison must document schema design, indexes, hardware, warm-up, repetitions and transaction semantics.

## Regulatory caution

The EU Battery Regulation is the primary legal source: https://eur-lex.europa.eu/eli/reg/2023/1542/oj. Passport obligations and timelines depend on battery category and the applicable legal provisions. This educational prototype is not a compliance assessment or a production digital battery passport.

