# AGENT.md

This package is an agentic-ready scientific workflow for hydride/NH3 materials.

## Agent-facing interfaces

- CLI: `hydride-agent ...` or `python -m hydride_agent.cli ...`
- FastAPI: `/databases`, `/skills`, `/chat`, `/skills/{skill_name}`
- Chainlit: `chainlit run chainlit_nh3_agent.py`
- MCP: `hydride_agent/mcp_server.py`

## Tool-use rules

1. Prefer structured skills before free-form answers.
2. Use `state_sequence_lookup` for composition-dependent physical-state sequences.
3. Use `state_complexity` for cross-family solid/mixed/liquid record counts.
4. Use `conductivity_loading` for DigBat conductivity versus NH3/BH4 loading.
5. Use `h2_release_loading` for DigHyd H2-release loading analysis.
6. Use `dual_axis_cross_database` only when comparing conductivity and H2-release evidence on separate y-axes.
7. Use `mechanism_synthesis` to separate direct evidence, indirect evidence, and hypotheses.
8. Do not infer solid/liquid state unless directly reported by the data.
9. Separate experimental observations, numerical-property trends, and mechanistic interpretations.
10. Report generated figures/tables as files in `outputs/`.

## Demo commands

```bat
python -m hydride_agent.cli check-data
python -m hydride_agent.cli list-skills
python -m hydride_agent.cli run-skill state_complexity
python -m hydride_agent.cli demo
```
