# Received attachments: provenance index

**Scope:** 14 user-supplied files for the Project Taycan research program. This repository currently contains **metadata only** for these original attachments, not the binary originals. The audit was performed against the exact uploaded files; see [SHA-256 and byte counts](../../data/manifests/received_attachments_2026-10-11.csv).

## Source families

| Category | Received files | Primary relevance | Handling |
| --- | ---: | --- | --- |
| Experimental battery data | NASA ZIP; Oxford MAT | External **cell-level** experiments | Original files held outside Git; provenance here |
| Porsche technical publications | AfterSales 2518.2 bulletin; 2021 Technical Feature PDF | Physical architecture and diagnostic test procedures | Upstream links, no original copyrighted copies |
| OBDb signal-set archive | Porsche-Taycan-main.zip | Candidate OBD signal definitions | Cite upstream version/license rather than publish duplicate |
| Porsche-derived article extraction | Markdown colado.md | Text duplicate of technical feature | Not republished |
| Unverified technical graphics | 8 PNGs | Structural image reference | Hashed only pending copyright/source/variant review |

## Official source links

- **NASA PCoE**: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- **Oxford Battery Degradation Dataset 1**: https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac
- **Porsche AfterSales bulletin (NHTSA-hosted)**: https://static.nhtsa.gov/odi/tsbs/2026/MC-11027127-0001.pdf
- **Porsche Technical Feature**: https://newsroom.porsche.com/en_AU/2021/products/technical-feature-the-porsche-taycan-23670.html
- **OBDb Porsche Taycan**: https://github.com/OBDb/Porsche-Taycan

## Important provenance distinctions

1. The Porsche technical article covers the **broader Taycan range** and dates to February 2021; separate measurements are necessary before claiming any component-specific value is validated for a **2022 Taycan 4S standard 79.2 kWh battery**.
2. NASA and Oxford measurements are **real experimental cell datasets**, not measurements from the Taycan battery pack, motor, or inverter.
3. The OBDb ZIP was supplied independently of the approved Stage 1 fixed Git revision: `85638dbc5f0a0b468e637de8b203417a0febbdbf`. Do **not** silently replace the approved signal catalog with the ZIP contents. OBDb includes a CC BY-SA 4.0 license; third-party rights/attribution must be honored.
4. Technical bulletin 2518.2 details professional **post-repair dielectric-strength and insulation-resistance testing**. Its module-level IR decision criteria are **not directly equivalent** to a diagnostic BMS/OBD threshold or a certified automated repair recommendation.
5. No external data has established the quantitative accuracy or safe operational use of this research simulator.
6. Source PDFs/images remain copyrighted or have unconfirmed rights, so this public repository contains only their references and cryptographic hashes.

## Data hygiene

- Keep original, possibly copyrighted files and unreviewed logs under local-only storage, never in public Git history by default.
- Before adding research artifacts, check sources, license, provenance, model-year/variant applicability and separation of training vs held-out records.
- The Stage 3 approved simulator source SHA-256 is `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`. No project model code was modified as part of this indexing action.
- Stage 4 awaits explicit approval; indexing files does not constitute progression to Stage 5.

**To incorporate original binary files**, explicitly confirm their redistribution rights and the repository's visibility; choose Git LFS only for authorized materials.
