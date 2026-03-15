# Decisões Técnicas — Bet Analytics Pipeline

## 1. Arquitetura Geral

**Decisão:** Arquitetura Medallion (Bronze → Silver → Gold)

**Por quê:** O pipeline lida com duas fontes de dados distintas (The Odds API + API-Football) que precisam ser cruzadas e transformadas em camadas. A arquitetura Medallion separa claramente as responsabilidades:

- **Bronze:** dado bruto da API, exatamente como veio (JSON → tabela). Serve como fonte da verdade histórica e permite reprocessamento.
- **Silver:** dado limpo, tipado, deduplicado e com relacionamentos resolvidos. É onde o dbt aplica transformações e testes de qualidade.
- **Gold:** agregações e KPIs prontos para consumo pelo Power BI.

**Alternativa descartada:** pipeline flat (ingestão direto para tabelas finais). Não permite reprocessamento, mistura responsabilidades de ingestão e transformação, e dificulta debug quando algo quebra.

---

## 2. Fontes de Dados

**Decisão:** The Odds API (v4) + API-Football (v3)

**Por que duas APIs:** nenhuma das duas sozinha cobre o escopo completo. A Odds API é forte em dados de apostas (odds, bookmakers, mercados) mas fraca em dados esportivos. A API-Football é o inverso. Combinadas, permitem cruzar odds com contexto esportivo — que é onde surgem os KPIs mais interessantes pro BI.

### The Odds API — 4 endpoints

| Endpoint | Dados retornados | Papel no pipeline |
|----------|-----------------|-------------------|
| `GET /v4/sports` | Lista de esportes (`key`, `group`, `title`, `active`, `has_outrights`) | Referência — dimensão de esportes |
| `GET /v4/sports/{sport}/events` | Jogos futuros/ao vivo (`id`, `sport_key`, `sport_title`, `commence_time`, `home_team`, `away_team`) | Core — lista de eventos |
| `GET /v4/sports/{sport}/odds` | Cotações por bookmaker/mercado. Aninhado: evento → bookmakers[] → markets[] → outcomes[] (`name`, `price`) | Core — dado central de apostas |
| `GET /v4/sports/{sport}/scores` | Resultados (`id`, `completed`, `scores[]` com `name` + `score`) | Core — placar dos eventos |

**Chave de junção interna:** campo `id` compartilhado entre events, odds e scores.

### API-Football — 6 endpoints

| Endpoint | Dados retornados | Papel no pipeline |
|----------|-----------------|-------------------|
| `GET /v3/leagues` | Ligas com país, temporadas e cobertura por temporada | Referência — dimensão de ligas |
| `GET /v3/teams` | Times com país, fundação e estádio | Referência — dimensão de times |
| `GET /v3/teams/statistics` | Stats agregadas por time/temporada: forma, gols por minuto, over/under, clean sheets, cartões, formações | Gold — métricas de performance |
| `GET /v3/fixtures` | Partidas com placar por período, liga, times, status, árbitro, estádio | Core — partidas com contexto esportivo |
| `GET /v3/fixtures/statistics` | Stats por partida por time: chutes, posse, cartões, passes. Formato `{type, value}` — pivotar no Silver | Core — estatísticas por jogo |
| `GET /v3/standings` | Classificação: posição, pontos, saldo, forma, desempenho casa/fora, zonas | Core — tabela da liga |

**Chave de junção interna:** `fixture.id` conecta fixtures ↔ fixtures/statistics. `league.id` + `season` conecta leagues ↔ standings ↔ teams/statistics. `team.id` conecta teams com todas as tabelas.

**Cruzamento entre APIs:** resolvido no Silver por mapeamento de **time + data** (não há ID compartilhado entre as duas APIs).

---

## 3. Stack de Ingestão

### HTTP Client

**Decisão:** httpx (async)

**Por quê:** o pipeline faz múltiplas chamadas a duas APIs diferentes (10 endpoints no total). httpx suporta async nativo, o que permite disparar requisições em paralelo sem bloquear. Também suporta sync para casos simples, tem API compatível com requests (curva de aprendizado baixa), e suporte nativo a HTTP/2.

**Alternativas consideradas:**
- **requests:** sync only. Para múltiplas chamadas de API, seria sequencial e mais lento. Não justifica quando httpx faz tudo que requests faz + async.
- **aiohttp:** async puro, mais complexo de configurar. httpx tem API mais limpa e é mais moderno.
- **urllib3:** baixo nível demais para esse caso de uso. requests e httpx são construídos em cima dele.

### Validação de Borda

**Decisão:** Pydantic v2 validando dados antes de gravar no Bronze

**Por quê:** os dados vêm de APIs externas que podem mudar o contrato sem aviso. Pydantic valida o schema na entrada do pipeline — se a API devolver um campo faltando, um tipo errado, ou uma estrutura diferente do esperado, o pipeline falha rápido e explícito ao invés de gravar lixo no Bronze e só descobrir o problema downstream.

**Alternativas consideradas:**
- **dataclasses:** não tem validação de tipos em runtime, só anotação. Precisaria de código manual pra validar.
- **marshmallow:** funcional, mas Pydantic v2 é mais rápido (core em Rust), tem melhor integração com type hints, e é o padrão de mercado atual.
- **validação manual (if/else):** frágil, verboso, não escala. Cada campo novo exige código novo.

---

## 4. Armazenamento

**Decisão:** Google BigQuery com 3 datasets separados (bronze, silver, gold)

**Por quê:** BigQuery é serverless — não precisa provisionar, escalar ou manter infraestrutura de banco. Tem integração nativa com dbt e Power BI. O tier gratuito (1TB de queries/mês + 10GB de armazenamento) é mais que suficiente para o volume deste projeto. Além disso, é a stack dominante em vagas de dados no mercado brasileiro.

**Por que 3 datasets:** cada camada da Medallion fica em um dataset separado no BigQuery. Isso dá isolamento de permissões (em produção, um analista de BI só precisa de acesso ao gold), facilita governança, e torna a arquitetura visível na própria organização do BigQuery.

**Alternativas consideradas:**
- **PostgreSQL:** excelente para OLTP e pipelines menores. Exigiria provisionar e manter um servidor (ou usar managed, que tem custo). Não tem vantagem sobre BigQuery para workloads analíticos neste escopo.
- **SQLite:** bom para prototipagem local, mas não escala, não tem integração nativa com dbt Cloud ou Power BI, e não demonstra habilidade com cloud.
- **DuckDB:** excelente para análise local e rápido para Parquet. Mas o objetivo é demonstrar pipeline cloud-native, e DuckDB não tem a integração com Power BI que BigQuery tem.

---

## 5. Transformação

**Decisão:** dbt Core

**Por quê:** dbt transforma SQL em código versionado, testável e documentável. Cada modelo é um SELECT, cada transformação tem linhagem rastreável (lineage), e os testes de qualidade ficam junto do código de transformação. Isso é exatamente o que se espera de um pipeline de dados moderno.

**Alternativas consideradas:**
- **SQL puro (scripts .sql):** funciona, mas sem linhagem, sem testes integrados, sem documentação automática, sem materialização configurável. É SQL sem as vantagens do framework.
- **pandas/Python:** transformação em Python é válida para dados não-estruturados ou lógica complexa, mas para transformações tabulares SQL é mais legível, mais performático no BigQuery, e mais alinhado com o que um time de dados espera.

---

## 6. Orquestração

**Decisão:** Prefect

**Por quê:** Prefect tem API Pythonica (decorators @flow, @task), setup leve, e UI gratuita para monitoramento. Para um projeto de portfólio onde o objetivo é demonstrar orquestração sem gastar dias configurando infra, Prefect é a escolha com melhor custo-benefício.

**Alternativas consideradas:**
- **Airflow:** padrão de mercado, mas setup pesado (webserver + scheduler + metadata DB). Faz sentido em produção corporativa, não em portfólio solo. Está no roadmap de aprendizado mas não justifica o overhead aqui.
- **cron:** funciona para agendamento simples, mas sem retry, sem logging centralizado, sem UI, sem dependência entre tasks. Não demonstra nada em portfólio.

---

## 7. Testes

**Decisão:** 3 camadas de testes

| Camada | Ferramenta | O que testa | Onde atua |
|--------|-----------|-------------|-----------|
| Contrato | Pydantic v2 | Schema dos dados da API (tipos, campos obrigatórios, formatos) | Borda — antes de gravar no Bronze |
| Unitário | pytest | Funções Python (extração, transformação, helpers) | Código do pipeline |
| Qualidade | dbt test | Integridade dos dados dentro do BigQuery (not_null, unique, accepted_values, relationships) | Silver e Gold |

**Por quê 3 camadas:** cada camada pega um tipo diferente de problema. Pydantic pega mudanças na API antes de poluir o Bronze. pytest pega bugs na lógica Python. dbt test pega problemas nos dados depois da transformação. Se qualquer camada falhar, as outras continuam protegendo.

**Alternativa descartada:** testar tudo com pytest. Possível tecnicamente, mas testes de qualidade de dados são mais naturais e legíveis como dbt tests (YAML declarativo), e testes de contrato de API são mais naturais como Pydantic models.

---

## 8. Ambiente

**Decisão:** uv

**Por quê:** uv resolve ambiente virtual + dependências + lockfile em um único comando. É ordens de magnitude mais rápido que pip e Poetry (core em Rust). Gera lockfile determinístico (`uv.lock`). É a ferramenta mais moderna do ecossistema Python e demonstra awareness de tooling atual.

**Alternativas consideradas:**
- **Poetry:** consolidado e maduro, mas significativamente mais lento que uv na resolução de dependências. Para um projeto novo, uv não tem desvantagem.
- **pip + venv:** funcional, mas sem lockfile nativo (precisa de pip-tools ou pip freeze manual). Mais propenso a problemas de reprodutibilidade.
- **conda:** voltado para data science com dependências C/Fortran. Pesado e desnecessário para este projeto.

---

## 9. Estrutura de Pastas

```
bet-analytics-pipeline/
├── .claude/
│   └── CLAUDE.md          # Instruções para o Claude Code
├── dbt_project/           # Modelos, testes e configs do dbt
├── docs/
│   └── DECISIONS.md       # Este arquivo
├── notebooks/             # Exploração e prototipagem
├── src/                   # Código Python do pipeline (ingestão, validação)
├── tests/                 # Testes pytest
├── README.md
└── pyproject.toml
```

**Por quê essa organização:**
- `src/` separado do `dbt_project/` porque são responsabilidades diferentes (ingestão Python vs transformação SQL).
- `docs/` para documentação que não é código.
- `notebooks/` para exploração das APIs e prototipagem — não vai pra produção, mas mostra o processo de investigação.
- `tests/` na raiz seguindo convenção pytest padrão.

---

## PENDENTE

- [ ] KPIs do Gold (quais métricas o Power BI vai exibir)
- [ ] Modelagem das tabelas Bronze / Silver / Gold
- [ ] Diagrama detalhado do fluxo de dados (ASCII para o README)
- [ ] Definição dos esportes/ligas que serão coletados