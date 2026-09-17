# Evaluation

Reference-datasæt og evalueringsmål for AI-laget (Technical Master §16).

Startmål: et repræsentativt, manuelt evalueret datasæt på tværs af lande,
kildetyper, relevante/irrelevante dokumenter, positive/negative cases,
manglende facts, dubletter og konflikter. 100–200 dokumenter er et
modningsmål, ikke en blokering for første slice.

Målte metrikker:

- relevance precision
- claim precision
- excerpt correctness
- entity resolution accuracy
- technology classification accuracy
- duplicate candidate precision
- human acceptance rate
- reviewtid (hvis instrumentering er mulig)

## Kørsel

Datasæt-formatet er JSONL — se `dataset.example.jsonl` og
`apps/api/app/evaluation.py`. Kør evalueringen med en konfigureret
AI-provider:

```bash
cd apps/api
uv run python -m app.evaluation --dataset ../../evaluation/dataset.jsonl
```

Rapporten indeholder relevance precision/recall, claim precision/recall
(på subjekt + predicate) og excerpt correctness. Kør den før hvert
modelskift eller promptversion-bump, og udbyg datasættet løbende med
manuelt vurderede dokumenter (100–200 er modningsmålet).
