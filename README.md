# Hydride NH3 Agent

Hydride NH3 Agent is a tool-gated research application for traceable analysis across three scientific backends:

- **NH3 Storage**: reported material state, phase behavior, conditions, and provenance;
- **DigBat**: ionic conductivity, temperature, composition, and DOI;
- **DigHyd**: reported H2 release, test conditions, composition, and DOI.

The language model is optional. It may route a question or summarize compact structured evidence, but all filtering, statistics, plotting, and file generation are performed by registered deterministic Python skills.

## Scientific workflow

The recommended article-aligned demonstration follows this sequence:

1. Compare physical-state diversity across material families.
2. Trace the LiBH4·xNH3 solid–liquid-like–solid sequence.
3. Analyze conductivity against NH3/BH4 under explicit temperature windows.
4. Compare reported H2 release without connecting non-comparable studies.
5. Separate direct evidence, indirect evidence, and a coordination-shell hypothesis.
6. Design USPEX/DFT/MD/MetaD validation and falsification tests.

## Registered skills

| Skill | Databases | Main output |
|---|---|---|
| `state_complexity` | NH3 Storage | Family-by-state count figure and screened CSV files |
| `state_sequence_lookup` | NH3 Storage | Composition-dependent state table with conditions and DOI |
| `conductivity_loading` | DigBat | DOI-aware conductivity figure and CSV files |
| `h2_release_loading` | DigHyd | Condition-aware H2-release scatter plot and CSV |
| `dual_axis_cross_database` | DigBat + DigHyd | Separate-axis cross-database figure |
| `mechanism_synthesis` | Session evidence | Evidence hierarchy, competing explanations, optional causal map |
| `computational_design` | Session evidence | USPEX/DFT/MD/MetaD workflow and falsification criteria |

## Representative questions

```text
Using the NH3 Storage dataset, compare the raw counts of solid, mixed/transition, and liquid records across material families. Highlight borohydrides and return the figure and supporting CSV files.
```

```text
Trace the reported state sequence of LiBH4·xNH3 from x = 1 to 3. List the composition, reported state, conditions, evidence type, confidence, and DOI. Determine whether the literature supports a solid–liquid-like–solid sequence.
```

```text
Using DigBat, plot ionic conductivity against NH3/BH4 ratio for LiBH4 near 305 ± 3 K and Mg(BH4)2 near 323 ± 3 K. Use one representative value per formula and DOI, aggregate multiple DOI in log10 conductivity space, and export the plotting data.
```

```text
Using DigHyd, compare reported H2 release across ammoniated borohydrides with NH3/BH4 > 0. Retain the host borohydride, loading, temperature, conditions, and DOI. Do not connect non-comparable studies.
```

```text
Based on the previous state, conductivity, and H2-release evidence, compare NH3 stoichiometry alone, cation effects, and coordination-shell reconstruction. Separate direct evidence, indirect evidence, and hypotheses, and generate an evidence-to-hypothesis map.
```

```text
Design a USPEX, molecular-dynamics, and metadynamics workflow to test whether coordination-shell switching explains LiBH4·NH3, LiBH4·2NH3, and LiBH4·3NH3. Specify collective variables, descriptors, expected observations, uncertainty checks, and falsification criteria.
```

Additional prompts are provided in [`examples/representative_queries.md`](examples/representative_queries.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

This public repository uses synthetic demonstration data in `data/demo/`. To use authorized full workbooks locally, place them in the ignored `data/raw/` directory or set `HYDRIDE_AGENT_DATA_DIR`.

To select another data directory:

```bash
export HYDRIDE_AGENT_DATA_DIR=/path/to/workbooks
```

Copy `.env.example` to `.env` only on your local machine. Never commit API keys.

## Run

### Chainlit

```bash
chainlit run chainlit_nh3_agent.py -w
```

### Streamlit

```bash
streamlit run app_streamlit.py
```

### API

```bash
uvicorn hydride_agent.api:app --reload --port 8000
```

### CLI

```bash
hydride-agent check-data
hydride-agent ask "Trace the reported state sequence of LiBH4·xNH3 from x = 1 to 3."
```

## Reproduce the representative outputs

```bash
python scripts/reproduce_all_examples.py
```

The script runs the five main database/mechanism demonstrations in one session and writes reports and artifacts to `outputs/reproduction/`.

## Data and public-release policy

The GitHub package contains **synthetic demonstration workbooks only**. They test code paths and must not be used for scientific conclusions. Full NH3 Storage, DigBat, and DigHyd workbooks are intentionally excluded from the public repository.

Before releasing any full dataset, verify:

- redistribution rights and database licenses;
- whether extracted literature text or figures may be shared;
- whether local paths, logs, emails, author metadata, or API keys are present;
- whether DOI-level records require a separate data citation.

## Testing

```bash
pytest -q
```

## Output boundary

The front ends receive only:

- a public report built from compact evidence;
- generated figures;
- explicit CSV exports.

`AgentResult.data_preview` remains empty, so unrestricted backend tables are not rendered directly.
