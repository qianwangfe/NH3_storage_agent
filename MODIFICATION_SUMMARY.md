# Modification summary

This release restructures the original prototype into a reproducible, tool-gated research application aligned with the NH3-storage manuscript workflow.

## Scientific changes

- Added seven explicit skills for state diversity, state-sequence retrieval, conductivity/loading analysis, H2-release analysis, cross-database comparison, mechanism synthesis, and computational design.
- Added robust parsing for ammoniated hydride formulas such as `LiBH4(NH3)2` and `Mg(BH4)2·1.8NH3`.
- Restricted the LiBH4 state-sequence workflow to host-specific, composition-resolved records and retained conditions, evidence type, confidence, and DOI.
- Added DOI-aware conductivity reduction with explicit temperature windows and log-space aggregation.
- Excluded parent hydrides by default from the ammoniated H2-release view and prevented lines between non-comparable studies.
- Added session-scoped evidence so mechanism and computational-design questions can build on earlier deterministic results.
- Added an evidence hierarchy and falsifiable USPEX/DFT/MD/MetaD validation plan.

## Software changes

- Rewrote the orchestration layer and fixed the original execution-order and indentation errors.
- Added deterministic fallback routing for all registered skills.
- Added Chainlit, Streamlit, FastAPI, and CLI entry points.
- Added synthetic English-language demonstration workbooks.
- Added a one-command reproduction script and automated tests.
- Added public-release documentation, dependency files, manifests, a license, citation metadata, and Git exclusions.

## Validation

The packaged release passes the included test suite:

```text
7 passed
```

The representative article-aligned workflow can be reproduced with:

```bash
python scripts/reproduce_all_examples.py
```
