---
tags:
  - modelo
  - previsao
  - quantidade
  - apresentacao
created: 2026-05-26
author: Daniel Ramazzotte
---

# Modelo de Previsão Diária — Quantidade de Propostas

**Experimento de Seleção de Modelo**
Validação Walk-Forward · 294 dias · 15 candidatos

---

## Contexto e Objetivo

**O que fazemos hoje:**
O modelo atual (Pipeline TPOT de produção) prevê diariamente a quantidade de propostas a serem analisadas.

**O problema identificado:**
A Pipeline Antiga apresenta instabilidade severa — em algumas datas, os erros chegam a **centenas de pontos percentuais**, tornando a previsão não confiável para planejamento.

**O que fizemos:**
Conduzimos um experimento sistemático comparando **91 configurações de modelo** divididas em 4 partes, usando validação histórica sobre **294 dias reais de previsão**.

> [!important] Meta de qualidade
> MAPE médio ≤ 5% (ideal) · ≤ 10% (aceitável)

---

## Como o Modelo Funciona

```
ClickHouse (dados históricos ~541 dias)
        ↓
  Agregação diária de propostas (etapa 16)
        ↓
  Feature Engineering
  ┌──────────────────────────────────────┐
  │  dia_semana   lag_1  lag_2  lag_3    │
  │  lag_0 (R$)   lag_4  lag_5  lag_6   │
  └──────────────────────────────────────┘
        ↓
  Janela deslizante (45 dias úteis de treino)
        ↓
  Modelo → Previsão do dia seguinte
```

**Features:** 8 variáveis — dia da semana + 6 lags de quantidade + 1 lag de valor monetário

**Janela de treino:** 45 dias úteis anteriores a cada previsão (replica exatamente o comportamento em produção)

---

## Metodologia de Validação

**Walk-Forward Cross-Validation** — a forma mais rigorosa para séries temporais

```
Fold 1:  [Treino: dias 1-45]  →  [Teste: dia 46]
Fold 2:  [Treino: dias 2-46]  →  [Teste: dia 47]
...
Fold N:  [Treino: dias N-45 a N-1]  →  [Teste: dia N]
```

| Parâmetro | Valor |
|-----------|-------|
| Folds totais avaliados | **294 dias úteis** (fev/2025 → abr/2026) |
| Janela de treino por fold | 45 dias úteis |
| Inclui sábados no treino | Sim |
| Métrica principal | MAPE (Erro Percentual Absoluto Médio) |
| Fonte de dados de teste | `backup_qtd.xlsx` (realizados reais) |

> [!note]
> Cada previsão é feita **sem ver dados futuros** — exatamente como em produção.

---

## Experimento — Visão Geral

4 partes · 91 configurações · 294 dias

- **Parte 1** · Modelos Simples
- **Parte 2** · Ensembles e Pipelines Avançadas
- **Parte 3** · Deep Learning e Séries Temporais
- **Parte 4** · Pipelines TPOT (produção avaliadas retrospectivamente)

---

## Parte 1 — Modelos Simples

Baseline com hiperparâmetros padrão, sem tuning.

| Modelo | MAPE Médio |
|--------|-----------|
| **ExtraTrees** | **10,02%** |
| **RandomForest** | **10,07%** |
| **XGBoost** | **10,31%** |
| GradientBoosting | 10,73% |
| HuberRegressor | 14,51% |
| Ridge | 14,74% |
| LinearRegression | 14,77% |

**Conclusão:** Modelos baseados em árvore (ExtraTrees, RandomForest, XGBoost) se destacam significativamente. Modelos lineares não capturam a não-linearidade do padrão de propostas.

---

## Parte 2 — Ensembles e Pipelines Avançadas

Seleção de variáveis, tuning de hiperparâmetros, ensembles.

| Modelo | MAPE Médio |
|--------|-----------|
| **VotingRegressor (ET + RF + XGB)** | **9,74%** |
| SelectKBest(k=5) + ExtraTrees | 10,07% |
| SelectKBest(k=6) + RandomForest | 10,17% |
| RandomForest (tuned) | ~10,1% |
| SelectKBest(k=3–4) + variantes | 10,1–10,2% |

**Conclusão:** O **VotingRegressor** (combinação de ExtraTrees + RandomForest + XGBoost) entregou o melhor resultado, reduzindo o MAPE em ~0,3 p.p. em relação ao melhor modelo simples. Ensembles superam modelos individuais.

---

## Parte 3 — Deep Learning e Séries Temporais

Modelos neurais (PyTorch) e abordagens clássicas de séries temporais.

| Modelo | MAPE Médio | Observação |
|--------|-----------|------------|
| LSTM | 11,52% | Rede recorrente, early stopping |
| CNN 1D | 11,88% | Convolucional temporal |
| Transformer | 12,37% | Atenção multi-head |
| NeuralProphet | 16,33% | Prophet com redes neurais |
| Auto-ARIMA | 22,38% | Modelo clássico estatístico |

**Conclusão:** Deep learning e ARIMA **não superam** os modelos de árvore para este problema. Com apenas 45 pontos de treino por fold, redes neurais não têm dados suficientes para aprender padrões complexos.

---

## Parte 4 — Pipelines TPOT (Avaliação Retrospectiva)

103 modelos `.pkl` do TPOT foram carregados e reavaliados nos mesmos 294 folds.

| Modelo (top TPOT) | MAPE Médio |
|------------------|-----------|
| FEAT+ABR-3 | 9,79% |
| SE(ETR)+MMS+BIN+SE(ELAS)+ABR | 9,83% |
| FEAT+ETR | 9,90% |
| SE(LINE)+SE(SGDR)+ABR | 9,91% |
| FEAT+ABR-4 | 9,93% |

**Conclusão:** As melhores pipelines TPOT ficam na faixa de **9,79–9,91%**, muito próximas do VotingRegressor (9,74%). A busca genética do TPOT não entregou vantagem significativa sobre um ensemble bem construído manualmente.

---

## Top 15 — Ranking Final (Folds Realinhados · 294 dias)

| # | Modelo | Arquitetura | MAPE Médio | Mediana | < 5% | < 10% |
|---|--------|-------------|:----------:|:-------:|:----:|:-----:|
| 1 | **FEAT+ABR-3** | FSS + AdaBoost (v3) | **9,81%** | 6,81% | 104/294 | 197/294 |
| 2 | **FEAT+ABR-4** | FSS + AdaBoost (v4) | **9,90%** | 6,47% | 112/294 | 189/294 |
| 3 | **VotingRegressor (ET+RF+XGB)** | Ensemble manual | **9,91%** | 7,28% | 105/294 | 196/294 |
| 4 | FEAT+ETR | FSS + ExtraTrees | 9,95% | 7,05% | 114/294 | 193/294 |
| 5 | SE(ETR)+MMS+BIN+SE(ELAS)+ABR | Stack ETR → Scale → Binarize → Stack ELAS → AdaBoost | 9,95% | 7,23% | 106/294 | 183/294 |
| 6 | RandomForest | — | 9,99% | 6,94% | 112/294 | 198/294 |
| 7 | SE(LINE)+SE(SGDR)+ABR | Stack LR → Stack SGD → AdaBoost | 10,10% | 6,76% | 106/294 | 197/294 |
| 8 | RandomForest (tuned) | — | 10,11% | 7,14% | 114/294 | 193/294 |
| 9 | SelectKBest(k=6)+RF | — | 10,12% | 6,72% | 109/294 | 194/294 |
| 10 | ExtraTrees | — | 10,25% | 7,02% | 101/294 | 182/294 |
| 11 | FEAT+ABR-2 | FSS + AdaBoost (v2) | 10,30% | 7,46% | 103/294 | 189/294 |
| 12 | SE(ETR)+MMS+SE(XGB)+PASS+ABR | Stack ETR → Scale → Stack XGB → AdaBoost | 10,53% | 8,01% | 94/294 | 183/294 |
| 13 | FEAT+ABR | FSS + AdaBoost (v1) | 10,55% | 7,97% | 90/294 | 187/294 |
| 14 | SelectKBest(k=5)+ExtraTrees | — | 10,97% | 7,39% | 99/294 | 178/294 |
| 15 | SE(SGDR)+SELE+ABR | Stack SGD → SelectFwe → AdaBoost | 11,00% | 7,84% | 96/294 | 179/294 |

---

## Pipeline Antiga — O Problema Real

A média altíssima (742%) é causada por **outliers extremos** — dias onde a previsão foi completamente equivocada:

| | Pipeline Antiga | Melhor Candidato |
|---|:---:|:---:|
| **MAPE Médio** | **742%** | **9,81%** |
| **Mediana** | 7,49% | 6,81% |
| **Q1** | 3,18% | 3,51% |
| **Q3** | 16,26% | 11,88% |
| **Previsões < 5%** | 125/303 | 104/294 |
| **Previsões < 10%** | 178/303 | 197/294 |

> [!warning] Interpretação
> A mediana de 7,49% indica que na maioria dos dias o modelo atual funciona razoavelmente. O problema são os **episódios de falha catastrófica** que puxam a média para cima.

---

## Distribuição do MAPE — Comparação Visual

```
Modelo                        |  Q1    Med    Q3     Outliers
──────────────────────────────────────────────────────────────
FEAT+ABR-3                    |  3,5%  6,8%  11,9%  ●●●
FEAT+ABR-4                    |  3,3%  6,5%  12,6%  ●●●
VotingRegressor (ET+RF+XGB)   |  3,4%  7,3%  12,7%  ●●●
RandomForest                  |  3,2%  6,9%  11,9%  ●●●
SelectKBest(k=6)+RF           |  3,4%  6,7%  12,2%  ●●●
ExtraTrees                    |  3,3%  7,0%  13,4%  ●●●
──────────────────────────────────────────────────────────────
Pipeline Antiga               |  3,2%  7,5%  16,3%  ●●●●●●●●●●●
                              |                      → até 143.000%+
```

Os candidatos top 15 têm **caudas significativamente menores** — os episódios de falha catastrófica da Pipeline Antiga não ocorrem nos novos modelos.

---

## Recomendação

> [!success] Modelo recomendado para produção
> **FEAT+ABR-3** (`FSS + AdaBoostRegressor`) — melhor MAPE médio (9,81%) e menor Q3 (11,88%)
>
> Alternativa interpretável: **VotingRegressor (ExtraTrees + RandomForest + XGBoost)**
> MAPE médio 9,91% · totalmente controlável · sem dependência do TPOT

**Por que o VotingRegressor é uma boa alternativa?**
- Totalmente transparente — sem caixa-preta do TPOT
- Fácil de re-treinar e auditar
- Performance estatisticamente equivalente ao top TPOT
- Elimina os episódios de falha catastrófica da Pipeline Antiga

**Ganho esperado vs Pipeline Atual:**
- Redução de **742% → ~9,9%** no MAPE médio
- Estabilidade: de **178/303** para **196/294** previsões abaixo de 10%

---

## Próximos Passos

| Ação | Responsável | Prazo |
|------|-------------|-------|
| Validar modelo nos dados de maio/2026 (out-of-sample) | Daniel | Semana 1 |
| Definir modelo final (TPOT-09/2025 vs VotingRegressor) | Gestores | Semana 1 |
| Implementar em produção com monitoramento de MAPE diário | Daniel | Semana 2 |
| Criar alerta automático quando MAPE > 15% | Daniel | Semana 2 |
| Avaliar extensão da metodologia para previsão de **valor** | Daniel | Semana 3 |

**Critério de aceite em produção:** MAPE médio mensal ≤ 10%, sem episódios > 50% em dias normais.

---

## Referências

- Notebook de experimento: [[experimento_qtd]]
- Notebook Top 15 realinhado: [[top15_qtd_realinhado]]
- Backup de previsões: `resultados/backup_qtd.xlsx`
- Modelos salvos: `modelos/quantidade/`
