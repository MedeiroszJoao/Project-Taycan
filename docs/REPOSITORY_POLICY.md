# Repository and provenance policy

1. **Access:** The repository is currently public. Do not upload original Porsche service manuals, proprietary diagrams, copyrighted media, identifiable vehicle logs or unpublished partner datasets without appropriate distribution rights.
2. **Provenance:** Track sources and file hashes. Retain stable upstream URLs and exact model/battery configurations. Separate primary-source evidence from secondary sources, assumptions, inference and synthetic results.
3. **Data separation:** Keep training, validation and held-out data partitions immutable once frozen; quarantine any accidentally exposed held-out derivatives and document the exposure.
4. **Approved code:** Import approved scientific artifacts unchanged; check SHA-256 before changes. A Git organization commit is not authorization to revise a scientific stage.
5. **Large files:** Git LFS is configured locally by the contributor; review each large file and licensing before staging. This repository scaffold intentionally does not create or overwrite `.gitattributes`.
6. **Safety:** No inference is a repair certification or electrical safety clearance. High-voltage physical interventions require trained personnel and official procedures.
