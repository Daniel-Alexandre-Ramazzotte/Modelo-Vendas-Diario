# Modelos que Superam a Pipeline em Produção — Quantidade

Análise do `top15_qtd_realinhado.ipynb`. Na base consistente (N=266 dias comuns, dias com erro operacional removidos via `Log_Erro`), a **Pipeline em Produção tem MAPE médio de 8,69%**. Dos 15 candidatos avaliados, **4 a superam em MAPE médio** — e todos com folga maior na mediana:

| # | Modelo | Origem (`.pkl`) | MAPE médio | Mediana |
|---|--------|-----------------|-----------|---------|
| 1 | `SE(LINE)+SE(SGDR)+ABR` | TPOT 2026-01-26 | **8,46%** | 6,28% |
| 2 | `FEAT+ABR(2)` | TPOT 2025-12-18 | 8,53% | 6,54% |
| 3 | `FEAT+ABR(4)` | TPOT 2026-01-21 | 8,59% | 6,36% |
| 4 | `SE(ETR)+MMS+BIN+SE(ELAS)+ABR` | TPOT 2025-07-23 | 8,59% | 6,62% |
| — | Pipeline em Produção | — | 8,69% | — |

Os quatro são pipelines gerados pelo TPOT (AutoML) em execuções reais de produção. Na avaliação do notebook, o `.pkl` fornece apenas a **arquitetura e os hiperparâmetros**: cada candidato é **retreinado do zero em cada fold** (`deepcopy` + `fit`), nos mesmos folds alinhados ao backup — portanto a comparação entre eles é de arquitetura, não de janela de treino. Todos preveem a quantidade diária de propostas a partir das mesmas features (`dia_semana` + `lag_1` a `lag_6`) e todos terminam em **AdaBoost** (boosting de árvores de decisão: árvores treinadas em sequência, cada uma corrigindo os erros da anterior).

> **Sobre as siglas**: o nome mostra só as etapas de primeiro nível do pipeline. `FEAT+ABR(2)` e `FEAT+ABR(4)` **não são o mesmo modelo** — o conteúdo do `FeatureUnion` (oculto na sigla) e os hiperparâmetros do AdaBoost diferem; o sufixo numérico é apenas colisão de nome.

## #1 — `SE(LINE)+SE(SGDR)+ABR` (MAPE 8,46% | mediana 6,28%)

Dois regressores lineares "dão opinião" antes do modelo final:

1. **`StackingEstimator(LinearSVR)`** — uma regressão por vetores de suporte linear, com regularização fortíssima (`C=0.001`, ou seja, previsão bem "suavizada"), é treinada e sua previsão é **anexada como feature extra** ao dataset.
2. **`StackingEstimator(SGDRegressor)`** — uma segunda regressão linear (gradiente descendente estocástico, perda epsilon-insensitive, sem intercepto) faz o mesmo: sua previsão vira mais uma feature.
3. **`AdaBoostRegressor`** (100 árvores, `learning_rate=0.5`, `loss=exponential`) — recebe as features originais **mais as duas previsões lineares** e aprende as correções não-lineares por cima.

**Intuição**: as duas etapas lineares capturam a tendência básica da série (nível e relação com os lags); o AdaBoost se concentra no que os lineares erram — efeitos de dia da semana e padrões não-lineares. É o melhor tanto em média quanto em mediana.

## #2 — `FEAT+ABR(2)` (MAPE 8,53% | mediana 6,54%)

1. **`FeatureUnion`** com dois ramos em paralelo: as **features originais** (ramo-cópia) e as **componentes principais via PCA** (solver randomizado) — combinações lineares dos lags ordenadas por variância, que funcionam como versões "descorrelacionadas" da série.
2. **`AdaBoostRegressor`** (100 árvores, `learning_rate=0.5`, `loss=exponential`) sobre o conjunto ampliado.

**Intuição**: lags consecutivos são muito correlacionados entre si; o PCA oferece ao boosting eixos alternativos (ex.: "nível médio da semana" vs. "tendência de alta/queda") em que os cortes das árvores podem ser mais eficientes.

## #3 — `FEAT+ABR(4)` (MAPE 8,59% | mediana 6,36%)

1. **`FeatureUnion`**: features originais (ramo-cópia) + **`Nystroem`** (kernel `additive_chi2`, `gamma=0.65`, 7 componentes) — uma aproximação de kernel que projeta os lags em um espaço não-linear de 7 dimensões.
2. **`AdaBoostRegressor`** (100 árvores, `learning_rate=1.0`, `loss=square`).

**Intuição**: mesma família do #2 (expandir as features antes do AdaBoost), mas a expansão é **não-linear** via kernel, e o boosting é mais agressivo (`learning_rate=1.0`). Segunda melhor mediana do ranking (6,36%).

## #4 — `SE(ETR)+MMS+BIN+SE(ELAS)+ABR` (MAPE 8,59% | mediana 6,62%)

O pipeline mais longo dos quatro, alternando empilhamento e transformação:

1. **`StackingEstimator(ExtraTreesRegressor)`** — uma floresta deliberadamente conservadora (`max_features=0.15`, `min_samples_leaf=9`, bootstrap) gera uma previsão "suave" que vira feature extra.
2. **`MinMaxScaler`** — normaliza tudo para [0, 1].
3. **`Binarizer(threshold=0.85)`** — converte cada feature em 0/1: vira um conjunto de *flags* indicando quais lags (e a previsão da floresta) estão no topo da escala — "ontem foi um dia de volume alto?".
4. **`StackingEstimator(ElasticNetCV)`** — uma regressão linear regularizada (L1+L2, `l1_ratio=0.65`, força escolhida por validação cruzada) prevê a partir dessas flags e anexa sua previsão como feature.
5. **`AdaBoostRegressor`** (100 árvores, `learning_rate=0.01`, `loss=square`) — boosting bem lento/conservador no topo.

**Intuição**: o pipeline transforma a série em sinais binários de "regime alto/baixo" e combina duas opiniões (floresta + linear) antes de um boosting de passo muito curto. É o mais regularizado dos quatro — empata com o #3 em média, mas tem a mediana mais alta do grupo.

## Leitura geral

- **Média vs. mediana**: os quatro vencem a produção por pouco na média (8,46–8,59% vs. 8,69%), mas a mediana (≈6,3–6,6%) indica erro tipicamente bem menor no dia a dia — a média é puxada por poucos dias atípicos.
- **Padrão comum**: nenhum dos vencedores usa as features cruas direto num único modelo; todos **enriquecem as features primeiro** (previsões empilhadas, PCA, kernel) e deixam o AdaBoost dar o veredito final.
