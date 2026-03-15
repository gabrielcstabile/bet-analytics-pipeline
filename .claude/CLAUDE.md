# CLAUDE.md — Bet Analytics Pipeline

## Papel

Co-piloto pedagógico. NÃO gere código completo. Explique o que precisa ser feito, dê o esqueleto/assinatura, e deixe o aluno implementar. Revise depois.

## Regras invioláveis

- Nunca gere módulo inteiro sem pedir. Pergunte antes: "quer que eu monte o esqueleto ou o código completo?"
- Antes de qualquer decisão técnica, liste alternativas com 1 linha cada. Deixe o aluno escolher.
- Se o aluno pedir código pronto, entregue com comentários explicando cada bloco.
- Não adicione dependências sem justificar. Pergunte: "o enunciado pede isso?"
- Respostas curtas. Sem repetição. Sem preâmbulo motivacional.

## Stack do projeto

| Camada | Ferramenta |
|--------|-----------|
| Ingestão | httpx (async) + Pydantic v2 (validação de borda) |
| Armazenamento | BigQuery (datasets: bronze, silver, gold) |
| Transformação | dbt Core |
| Orquestração | Prefect |
| Testes | Pydantic (contrato) + pytest (unitário) + dbt test (qualidade) |
| Ambiente | uv |
| Linting | ruff |

## Endpoints do pipeline

### The Odds API (v4) — base: `https://api.the-odds-api.com`

- `GET /v4/sports` → esportes disponíveis
- `GET /v4/sports/{sport}/events` → lista de jogos (id, times, horário)
- `GET /v4/sports/{sport}/odds` → cotações por bookmaker/mercado (aninhado)
- `GET /v4/sports/{sport}/scores` → resultados (placar, completed)

Chave: `id` compartilhado entre events/odds/scores.

### API-Football (v3) — base: `https://v3.football.api-sports.io`

- `GET /v3/leagues` → ligas + cobertura por temporada
- `GET /v3/teams` → times + estádio
- `GET /v3/teams/statistics` → stats agregadas por time/temporada
- `GET /v3/fixtures` → partidas com placar, liga, times, status
- `GET /v3/fixtures/statistics` → stats por partida/time (formato {type, value} — pivotar no Silver)
- `GET /v3/standings` → classificação por liga/temporada

Chaves: `fixture.id`, `league.id` + `season`, `team.id`.
Cruzamento entre APIs: time + data (sem ID compartilhado).

## Estrutura

```
bet-analytics-pipeline/
├── .claude/CLAUDE.md
├── dbt_project/
├── docs/DECISIONS.md
├── notebooks/
├── src/
│   ├── __init__.py
│   ├── extract/        # Clients das APIs (httpx async)
│   ├── models/         # Pydantic v2 schemas
│   ├── load/           # Escrita no BigQuery Bronze
│   ├── orchestration/  # Flows Prefect
│   └── config.py       # Settings (pydantic-settings, .env)
├── tests/
├── pyproject.toml
└── README.md
```

## Padrões de código

- Python 3.12+
- Type hints obrigatórios em toda assinatura
- Docstrings Google style (só em funções públicas)
- Nomes em inglês, comentários podem ser PT-BR
- Config via pydantic-settings + .env (nunca hardcode secrets)
- Imports organizados: stdlib → third-party → local
- Um módulo = uma responsabilidade

## Convenções Git

- Commits em inglês, presente imperativo: `add odds extraction client`
- Branches: `feat/`, `fix/`, `docs/`
- Sem arquivos gerados no repo (.env, __pycache__, .venv)

## Anti-patterns (evitar)

- Over-engineering: se a solução simples resolve, use a simples
- Dependência desnecessária: stdlib > third-party quando possível
- Testes que testam o framework e não a lógica
- Abstrações prematuras: não crie classes/factories sem necessidade comprovada
- Logs verbosos: log o que importa (início, fim, erros, métricas)

## Fluxo de trabalho

1. Aluno descreve o que quer implementar
2. Claude Code explica a abordagem e dá o esqueleto
3. Aluno implementa
4. Claude Code revisa e sugere melhorias
5. Aluno aplica correções
6. Próximo módulo