# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Sistema de previsão diária de vendas usando AutoML (TPOT). Dois modelos independentes:
- **Quantidade** (`scripts/producao/projecoes_qtd.py`): prevê número de propostas a serem analisadas
- **Valor** (`scripts/producao/projecoes_valor.py`): prevê valor monetário das propostas

Os scripts só executam em dias úteis brasileiros (verificam feriados e fins de semana via `workadays`).

## Estrutura de pastas

```
notebooks/
  producao/      versão interativa dos modelos de produção (projecoes_qtd/valor.ipynb)
  experimentos/  experimentos, viés, top15 e incremento por canal/produto
scripts/
  producao/      scripts de produção (projecoes_qtd.py, projecoes_valor.py)
  experimentos/  builders de notebook (_build_*) e protótipos (_exp_*)
  render_marp.py utilitário que gera a apresentação HTML a partir do docs/*.md
docs/            documentação (.md), apresentações (.md/.html) e anotações
saidas/          planilhas/CSVs gerados (comparativos, recalc, etc.)
modelos/         modelos .pkl: quantidade/, valor/ e arquivo/{fracos,diversos}
resultados/      backups oficiais lidos pelos modelos (backup_qtd/valor.xlsx)
estudo/          dados e análises exploratórias
cache/           cache de queries/predições (ignorado pelo git)
lightning_logs/  artefatos de treino (ignorado pelo git)
```

**Caminhos relativos:** notebooks e scripts resolvem a raiz do projeto procurando o
`CLAUDE.md` (subindo a árvore de diretórios) e operam a partir dela. Por isso podem ser
movidos de pasta sem quebrar os caminhos `cache/`, `modelos/`, `resultados/`, etc.

## Executando os scripts

```bash
python scripts/producao/projecoes_qtd.py
python scripts/producao/projecoes_valor.py
```

Os notebooks em `notebooks/producao/` são a versão interativa dos mesmos scripts; os de
`notebooks/experimentos/` são usados para desenvolvimento e exploração.

## Dependências necessárias

```bash
pip install pandas joblib scikit-learn tpot clickhouse-connect workadays openpyxl
```

## Arquitetura e fluxo de dados

```
ClickHouse DB (45 dias históricos)
    ↓
Agregação diária + feature engineering
    ├── dia_semana (0=seg, 6=dom)
    └── lag_1 a lag_6 (qtd) / lag_1 a lag_7 (valor, inclui fila)
    ↓
TPOT AutoML (60 gerações, população 60)
    ↓
Validação MAPE (aceitável: 1–5%)
    ├── Aprovado → salva .pkl + atualiza backup Excel
    └── Reprovado → retreina (máx 4x para qtd, 3x para valor)
```

**Modelo de valor** usa dois queries: dados de propostas (etapa 16) + dados de fila (etapa 15), que são mesclados para criar o feature `lag_7`.

## Convenções de arquivo

- Modelos salvos em `modelos/quantidade/` e `modelos/valor/` com nome `modelo_treinado-YYYY-MM-DD.pkl`
- Modelos com MAPE ruim são arquivados em `modelos/arquivo/fracos/`
- `resultados/backup_qtd.xlsx` e `resultados/backup_valor.xlsx` registram histórico de previsões e MAPE
- O script sempre carrega o modelo mais recente (ordenado por data de modificação)

## Banco de dados

ClickHouse em `10.101.150.150:8123`. As tabelas principais são:
- `crefaz.ft_proposta`: dados de propostas (etapa 16)
- `crefazon15m.dbo_propostastatushistorico`: histórico de status (etapa 15, usado em valor)

## Critérios de qualidade do modelo

| Métrica | Qtd | Valor |
|---------|-----|-------|
| MAPE ideal | 1–5% | 1–5% |
| MAPE máximo aceito | 5% | 5% |
| Tentativas de retreino | 4 | 3 |
| `n_jobs` TPOT | 1 | 6 |

## Convenções dos notebooks de experimento

- **Tabelas de ranking sempre com o nome do modelo como COLUNA, nunca como índice/nome
  da linha.** Vale para `experimento_qtd_vies.ipynb` e `experimento_valor_vies.ipynb`
  (ex.: `df_ranking_int`, `_comp`). Use o helper `_com_modelo(df, nome='Modelo')` ao
  exibir (`display(_com_modelo(...))`); mantenha o DataFrame interno com o índice porque
  o código a jusante usa `.loc[modelo]`/`.index`. As tabelas de `build_table` já trazem o
  modelo na coluna `Pipeline`, então já atendem a regra.
