# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Sistema de previsão diária de vendas usando AutoML (TPOT). Dois modelos independentes:
- **Quantidade** (`projecoes_qtd.py`): prevê número de propostas a serem analisadas
- **Valor** (`projecoes_valor.py`): prevê valor monetário das propostas

Os scripts só executam em dias úteis brasileiros (verificam feriados e fins de semana via `workadays`).

## Executando os scripts

```bash
python projecoes_qtd.py
python projecoes_valor.py
```

Os notebooks (`.ipynb`) são a versão interativa dos mesmos scripts — usados para desenvolvimento e exploração.

## Dependências necessárias

```bash
pip install pandas joblib scikit-learn tpot clickhouse-connect workadays openpyxl
```

## Arquitetura e fluxo de dados

```
ClickHouse DB (55 dias históricos)
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

- Modelos salvos em `Modelos_qtd/` e `Modelos_valor/` com nome `modelo_treinado-YYYY-MM-DD.pkl`
- Modelos com MAPE ruim são movidos para `modelos fracos/`
- `backup_qtd.xlsx` e `backup_valor.xlsx` registram histórico de previsões e MAPE
- O script sempre carrega o modelo mais recente (ordenado por data de modificação)

## Caminhos hardcoded

Os scripts usam caminhos absolutos Windows apontando para `M:\03-Relatorios\Projecoes\`. Se rodar em outro ambiente, ajuste as variáveis de caminho no início de cada script.

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
