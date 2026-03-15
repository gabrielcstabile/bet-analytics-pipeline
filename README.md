# Bet Analytics Pipeline

Pipeline ELT de dados de apostas esportivas com arquitetura Medallion, ingestão de APIs públicas, transformação com dbt e visualização em Power BI.

## Arquitetura

```
┌─────────────┐     ┌─────────────┐
│ The Odds API│     │API-Football │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 │
          httpx (async)
                 │
          Pydantic v2
         (validação de borda)
                 │
    ┌────────────▼────────────┐
    │   BigQuery — Bronze     │
    │   (dado bruto da API)   │
    └────────────┬────────────┘
                 │
           dbt Core
          + dbt tests
                 │
    ┌────────────▼────────────┐
    │   BigQuery — Silver     │
    │ (limpo, tipado, joins)  │
    └────────────┬────────────┘
                 │
           dbt Core
          + dbt tests
                 │
    ┌────────────▼────────────┐
    │   BigQuery — Gold       │
    │   (KPIs, agregações)    │
    └────────────┬────────────┘
                 │
           Power BI
```

## Stack

| Camada | Ferramenta | Justificativa |
|--------|-----------|---------------|
| Ingestão | httpx (async) | Requisições paralelas a múltiplas APIs |
| Validação | Pydantic v2 | Contrato de dados na borda, antes do Bronze |
| Armazenamento | BigQuery | Serverless, tier gratuito, integração nativa com dbt e Power BI |
| Transformação | dbt Core | SQL versionado, testável, com linhagem rastreável |
| Orquestração | Prefect | Setup leve, API Pythonica, UI gratuita |
| Testes | Pydantic + pytest + dbt test | 3 camadas: contrato, unitário, qualidade |
| Ambiente | uv | Rápido, lockfile determinístico, resolve tudo em um comando |
| Linting | ruff | Substitui black + isort + flake8 em uma ferramenta |

## Estratégia de Testes

O pipeline usa 3 camadas de teste, cada uma cobrindo um tipo de falha diferente:

| Camada | Ferramenta | O que pega | Onde atua |
|--------|-----------|------------|-----------|
| Contrato | Pydantic v2 | API mudou o schema, campo faltando, tipo errado | Antes de gravar no Bronze |
| Unitário | pytest | Bug na lógica Python de extração/transformação | Código em `src/` e `tests/` |
| Qualidade | dbt test | Nulos, duplicatas, valores inválidos nos dados | Silver e Gold no BigQuery |

## Decisões Técnicas

As justificativas detalhadas de cada escolha tecnológica estão documentadas em [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) instalado
- Conta GCP com BigQuery habilitado
- API keys: [The Odds API](https://the-odds-api.com/) + [API-Football](https://www.api-football.com/)

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/gabrielcstabile/bet-analytics-pipeline.git
cd bet-analytics-pipeline

# Instalar dependências
uv sync

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas API keys e credenciais GCP
```

## Como executar

```bash
# TODO: comandos de execução serão adicionados conforme implementação
```

## Como rodar os testes

```bash
# Testes unitários
uv run pytest

# Testes dbt
cd dbt_project && dbt test
```

## Estrutura do Projeto

```
bet-analytics-pipeline/
├── .claude/CLAUDE.md       # Instruções para o Claude Code
├── dbt_project/            # Modelos, testes e configs do dbt
├── docs/
│   └── DECISIONS.md        # Decisões técnicas documentadas
├── notebooks/              # Exploração de APIs e prototipagem
├── src/
│   ├── extract/            # Clients das APIs (httpx async)
│   ├── models/             # Schemas Pydantic v2
│   ├── load/               # Escrita no BigQuery
│   ├── orchestration/      # Flows Prefect
│   └── config.py           # Settings via pydantic-settings
├── tests/                  # Testes pytest
├── pyproject.toml
└── README.md
```

## Autor

**Gabriel Correia Stabile** — [GitHub](https://github.com/gabrielcstabile)