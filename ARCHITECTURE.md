# Architecture

```text
User question
  -> Chainlit / Streamlit / API / CLI
  -> optional routing model or deterministic router
  -> registered database skill
  -> read-only DatabaseRouter
  -> deterministic screening, statistics, and plotting
  -> compact structured evidence
  -> optional evidence-constrained synthesis model
  -> public report and explicit artifacts
```

## Trust boundary

- Models do not execute arbitrary Python.
- Models do not receive unrestricted workbook tables.
- Every analysis must map to one registered skill.
- State, conductivity, and hydrogen-release datasets retain distinct scientific roles.
- Cross-database context motivates a mechanism but does not prove microscopic coordination.
- Session evidence is stored only as compact summaries and is used by the mechanism and computational-design skills.

## Skill contract

```python
name: str
description: str
databases: tuple[str, ...]
produces_figure: bool
produces_table: bool
matches(request: str) -> float
run(context: SkillContext) -> SkillResult
```

A `SkillResult` contains generated paths, compact evidence, and an execution message.
