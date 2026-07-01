# Top 4 Modelos TPOT — Valor

Análise do `top15_valor_realinhado.ipynb`. Os 9 pipelines TPOT do estudo foram resgatados dos `.pkl` de produção (`modelos/valor/modelo_treinado-AAAA-MM-DD.pkl`) — cada um é o vencedor da busca AutoML de um dia específico. Na avaliação, são **retreinados do zero em cada fold** (features BASE, janela 45), nos mesmos folds alinhados ao backup; 4 dos 9 foram descartados por incompatibilidade com o sklearn atual. Estes são os 4 melhores no ranking (base consistente, N=266):

| # | Modelo | pkl de origem | MAPE médio | Mediana | Desvio |
|---|--------|--------------|-----------|---------|--------|
| 1 | `SE(ETR)+ABR` | 2026-03-31 | 9,72% | 7,00% | 13,15% |
| 2 | `FEAT+MMS+SE(ABR)+RFR` | 2025-07-19 | 10,12% | 7,81% | 11,12% |
| 3 | `FEAT+SE(ELAS)+SELE+ABR` | 2026-01-06 | 10,55% | 8,34% | 11,57% |
| 4 | `SELE+MAS+SE(ABR)+NRM+SE(ELAS)+SS+VT+ABR` | 2026-02-19 | 11,21% | 8,35% | 13,32% |
| — | Pipeline em Produção | retreinada ~diariamente | **9,15%** | **6,89%** | 11,58% |

**Nenhum dos 4 bate a Pipeline em Produção** — nem na média, nem na mediana. Isso não contradiz o fato de a produção também ser TPOT: ela **refaz a busca AutoML quase todo dia útil**, enquanto aqui cada pkl é uma arquitetura congelada de um dia específico sendo reaplicada a todo o histórico. A arquitetura de um dia bom não generaliza; o que vence a produção no estudo são os candidatos novos `(EXT)` (ver `explicacao_modelos_top15_valor.md`).

> **Atenção à sigla:** ela mostra só os passos de primeiro nível do pipeline. `SE(X)` = `StackingEstimator(X)`: treina o modelo X e **anexa a predição dele como feature extra** para os passos seguintes (as features originais continuam passando adiante). `FEAT` = `FeatureUnion`, cujo conteúdo interno a sigla esconde — abaixo está a arquitetura real de cada pkl.

## #1 — `SE(ETR)+ABR` (MAPE 9,72% | mediana 7,00%)

O mais simples e melhor dos quatro, com só dois passos:

1. `SE(ExtraTreesRegressor)` — floresta bem regularizada (`max_features=0.2`, `min_samples_leaf=17`, bootstrap) cuja predição vira feature extra;
2. `AdaBoostRegressor(n_estimators=100, learning_rate=0.001, loss='square')` — o learning rate minúsculo torna o boosting quase estático: na prática, um comitê de 100 árvores rasas pouco adaptativo, ou seja, **muito conservador**.

A composição "uma floresta regularizada alimentando um booster manso" explica o bom resultado relativo: pouca capacidade de superajustar. Ainda assim, tem o segundo pior desvio do grupo (13,15%) — sofre nos dias atípicos.

## #2 — `FEAT+MMS+SE(ABR)+RFR` (MAPE 10,12% | mediana 7,81%)

O mais complexo dos quatro. O `FEAT` esconde um **FeatureUnion aninhado em dois níveis** que empilha as predições de 4 modelos como features:

- `SE(LinearSVR)` (C=10, perda squared-epsilon-insensitive);
- dentro de um segundo FeatureUnion: `SE(RandomForestRegressor)` regularizado (`min_samples_leaf=16`) e um sub-pipeline `SE(DecisionTree max_depth=7)` → `SE(XGBRegressor)` → 2× `MaxAbsScaler` → `Normalizer`.

Depois: `MinMaxScaler` → `SE(AdaBoostRegressor)` → **`RandomForestRegressor` final** (`bootstrap=False`, `min_samples_leaf=2`). São 5 modelos servindo de geradores de feature para uma floresta final — um stacking profundo. Curiosamente tem o **menor desvio do grupo (11,12%)** e o menor máximo, mas a complexidade não se converte em mediana melhor.

## #3 — `FEAT+SE(ELAS)+SELE+ABR` (MAPE 10,55% | mediana 8,34%)

1. `FEAT`: une (a) `SE(Pipeline: SelectFromModel(ExtraTrees) → MinMaxScaler → RandomForest)` — um mini-pipeline inteiro cuja predição vira feature — e (b) um passthrough (`FunctionTransformer(copy)`, que só repassa as features originais);
2. `SE(ElasticNetCV)` — adiciona a visão de um modelo **linear** regularizado;
3. `SelectFromModel(ExtraTrees, threshold=0.2)` — corta as features menos importantes;
4. `AdaBoostRegressor(n_estimators=100, loss='exponential')`.

Combina árvore + linear como features e seleciona antes do booster final. A perda exponencial do AdaBoost é mais sensível a outliers — possível razão da mediana fraca.

## #4 — `SELE+MAS+SE(ABR)+NRM+SE(ELAS)+SS+VT+ABR` (MAPE 11,21% | mediana 8,35%)

Cadeia linear de 8 passos: `SelectFromModel(ExtraTrees, threshold=0.05)` → `MaxAbsScaler` → `SE(AdaBoost lr=0.1)` → `Normalizer(norm='max')` → `SE(ElasticNetCV l1_ratio=0.2)` → `StandardScaler` → `VarianceThreshold(0.05)` → `AdaBoostRegressor(lr=0.1, loss='exponential')`. É o padrão típico de busca TPOT longa: empilhar reescalonamentos sucessivos (3 escalas diferentes!) e predições intermediárias. Tem o **pior desvio do grupo (13,32%)** — a cadeia longa não estabilizou nada.

## Leitura geral

- **AdaBoost por toda parte**: é o regressor final em 3 dos 4 (e aparece como gerador de feature nos outros passos). `SelectFromModel(ExtraTrees)` é o seletor de features favorito da busca. Esse é o "sotaque" do TPOT desta base.
- **Complexidade não paga**: o ranking interno é quase monotônico na simplicidade — o pipeline de 2 passos (#1) vence o de 8 passos (#4) com folga.
- **O valor real destes pkls é diagnóstico**: eles mostram o que a produção constrói num dia típico. Congelados, todos perdem para a produção retreinada diariamente (9,15%) e para os candidatos novos com features estendidas (8,49–9,14%).
