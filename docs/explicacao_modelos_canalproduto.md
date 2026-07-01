# Modelos com canal e produto — como cada abordagem é feita

Documento de referência do notebook **`incremento_canal_produto.ipynb`**. Explica, sem código,
o que cada variante faz, como fica a base de treinamento e como as comparações são montadas.

O estudo testa se enriquecer os modelos pré-selecionados com informação de **canal** (`canalid`
→ `crefaz.dim_canal.nome`) e **produto** (`produtoid` → `crefaz.dim_produto.produto`) melhora a
previsão diária frente à **pipeline antiga em produção**. Período: **janeiro/2026 em diante**.

---

## 1. Conceitos comuns a todas as abordagens

- **Grão**: um registro por **dia útil**. O alvo é o **total do dia** (qtd = nº de propostas na
  etapa 16; valor = R$ das propostas na etapa 16).
- **Previsão dia-à-frente, com re-treino por fold (walk-forward)**: para prever um dia `D`, a
  arquitetura é **re-treinada do zero** usando a janela dos dias úteis imediatamente anteriores
  a `D` (45 dias; 90 no candidato `ExtraTrees(EXT,j90)`). Isso se repete para cada dia avaliado.
- **Anti-vazamento**: nenhuma feature usa informação do próprio dia previsto. Tudo que vem de
  canal/produto é **defasado** (≥1 dia útil). No `+seg_pca` o PCA é **re-ajustado dentro de cada
  fold** (só no treino), nunca no conjunto inteiro.
- **Dias removidos**: domingos/feriados nunca são previstos; dias marcados no `Log_Erro`
  (incidentes operacionais) são removidos da comparação para não penalizar/beneficiar ninguém.
- **Comparação justa**: todas as abordagens e a Pipeline Antiga são avaliadas exatamente sobre o
  **mesmo conjunto de datas** (`COMMON_DATES`, interseção de todas), contra o **realizado
  recomputado** da base (não o realizado “parcial” que estava gravado no backup antigo).

### Métricas
- **MAPE** (erro percentual absoluto médio) — magnitude relativa do erro.
- **Viés** = média de (`realizado − predito`) — sinal: positivo ⇒ modelo **subestima**;
  negativo ⇒ **superestima**.
- **MAE** = média de |`realizado − predito`| — magnitude absoluta.
- **Safra mensal**: as mesmas métricas quebradas **mês a mês**, por modelo × abordagem.

---

## 2. As abordagens (variantes)

As **4 primeiras são top-down** (preveem o total do dia direto, mudando só o conjunto de
features). A **5ª é bottom-up** (estratégia diferente: desagrega e reagrega).

### 2.1 `base` — features atuais de produção
Reproduz o modelo que já roda. **Nenhuma** informação de canal/produto.

- **Quantidade**: `dia_semana`, `lag_0` (R$ do dia anterior), `lag_1..lag_6` (qtd dos 6 dias
  úteis anteriores).
- **Valor**: `dia_semana`, `lag_0` (qtd do dia anterior), `lag_1..lag_6` (R$ dos 6 dias
  anteriores), `lag_7` (tamanho da **fila** — etapa 15 — do dia anterior).
  - O candidato `ExtraTrees(EXT,j90)` usa a base estendida **EXT**: além do acima,
    `dia_mes`, `semana_mes`, `fim_mes`, `ma3_valor`, `ma5_valor`, `ticket_1`, `ma3_ticket`,
    `qnt_lag2`.

### 2.2 `+mix` — composição dominante de ontem (2 features)
Acrescenta à `base` **duas** features defasadas:
- `share_canal_top` — fração do volume de **ontem** concentrada no **canal** mais forte do dia.
- `share_produto_top` — idem para o **produto** mais forte.

É um resumo leve do “mix” (quão concentrada estava a operação no dia anterior), sem explodir a
dimensionalidade.

### 2.3 `+seg` — volume por segmento, cru (muitas colunas)
Acrescenta à `base` o **volume de cada canal e de cada produto**, em **vários lags** (`SEG_LAGS =
1,2,3,4,5` dias úteis):
- **Quantidade**: `qtd_canal<id>_lag{k}` e `qtd_prod<id>_lag{k}`.
- **Valor**: idem em R$ (`valor_canal<id>_lag{k}`, `valor_prod<id>_lag{k}`) **e** em quantidade
  (`qtd_canal<id>_lag{k}`, `qtd_prod<id>_lag{k}`).

Dá ao modelo a série recente de cada segmento separadamente. **Atenção**: gera dezenas de colunas
(qtd) a ~140 colunas (valor) para uma janela de ~45 linhas → **forte risco de overfit**. Existe
de propósito, como contraste do `+seg_pca`.

### 2.4 `+seg_pca` — as mesmas features de `+seg`, comprimidas
Pega exatamente as colunas do `+seg`, aplica **StandardScaler + PCA** e mantém só as componentes
que somam **≥ 80% da variância**. A base original passa direto; só o bloco de segmento é
comprimido. O PCA é re-ajustado **por fold** (anti-vazamento). Objetivo: aproveitar o sinal dos
segmentos sem o excesso de colunas que faz o `+seg` cru sofrer.

### 2.5 `bottom-up` — um modelo por célula `canal × produto`, depois soma
Abordagem **hierárquica**, fundamentalmente diferente das anteriores:
1. Define as células `canalid × produtoid`. Para manter tratável, fica com as **`TOP_K_CELLS`
   (12) maiores** por volume no período; todo o resto é somado em uma célula **`outros`**. Assim a
   **soma das células reconstrói exatamente o total** (há um *sanity check* no notebook imprimindo
   `max|diff| ≈ 0`).
2. Treina **a mesma arquitetura, uma vez por célula × fold**, prevendo o volume **daquela célula**.
   Cada célula usa as features **da própria célula**: `dia_semana`, `lag_0` (medida auxiliar de
   ontem — R$ para qtd, qtd para valor) e `lag_1..lag_6` (a própria série da célula defasada).
3. Soma as previsões das células (com **clip em ≥ 0**, pois volume não é negativo) → total do dia.

A pergunta que essa variante responde: **desagregar e reagregar prevê melhor do que prever o total direto?**

> **Limitações honestas do bottom-up** (estão no notebook): as features especiais do agregado **não
> existem por célula** — o `lag_7` de fila e os extras do `EXT` são medidas agregadas. Então o
> modelo por célula usa só a base simples (`dia_semana` + `lag_0..lag_6` da célula), enquanto o
> top-down de cada modelo mantém sua base completa. É o preço de desagregar.

---

## 3. Como fica a base de treinamento

### Top-down (`base`, `+mix`, `+seg`, `+seg_pca`)
Uma única matriz **diária**: 1 linha por dia útil, colunas = features da variante, alvo = total do
dia. O notebook imprime um bloco **“BASE DE TREINAMENTO”** mostrando shape, intervalo de datas e as
últimas linhas (base + mix + amostra das colunas de segmento). A cada dia previsto, o modelo é
treinado nas **últimas 45 linhas** (90 no `ExtraTrees`) anteriores àquele dia.

Esquema (quantidade, ilustrativo):

| data | qntd (alvo) | dia_semana | lag_0 (R$ ontem) | lag_1..lag_6 (qtd) | [+mix] | [+seg…] |
|------|-------------|------------|------------------|--------------------|--------|---------|
| …    | 1.234       | 2          | 9,8M             | 1.180 / 1.205 / …  | 0,42 / 0,37 | … |

### Bottom-up
**Várias** matrizes — uma por célula. Cada matriz tem a estrutura da `base` simples, mas a série é a
**daquela célula** (ex.: célula `c3_p10` = canal 3 × produto 10). Há `TOP_K_CELLS + 1` matrizes, e
cada uma é re-treinada na sua janela de 45/90 dias por fold. O total do dia é a soma das previsões
de todas as células.

Esquema (uma célula, quantidade):

| data | y = qntd da célula | dia_semana | lag_0 (R$ da célula ontem) | lag_1..lag_6 (qntd da célula) |
|------|--------------------|------------|----------------------------|-------------------------------|
| …    | 230                | 2          | 1,7M                       | 210 / 225 / …                 |

---

## 4. Modelos avaliados

Cada modelo roda em **todas** as variantes acima.

- **Quantidade (2):** `SE(LINE)+SE(SGDR)+ABR`, `SE(ETR)+MMS+BIN+SE(ELAS)+ABR` (pipelines TPOT
  carregados de `.pkl`).
- **Valor (3):** `SE(ETR)+ABR` (TPOT), `ExtraTrees(EXT,j90)` (janela 90, base EXT),
  `Voting(GBR+XGB+RFR)` (ensemble por média de GradientBoosting + XGBoost + RandomForest).

Como cada arquitetura é re-treinada por fold, passar uma matriz de features diferente (ou treinar
por célula) **não exige alterar o `.pkl`** — só muda o que entra no `fit`.

---

## 5. Como ler as comparações no notebook

Tudo deriva de uma **tabela mestra (`MASTER`)** em formato longo: uma linha por
`(parte, modelo, variante, dia)` com `realizado`, `predito`, `erro` (com sinal), `|erro|` e `APE`.

1. **Ranking por modelo × variante** (qtd e valor): MAPE médio, mediana, viés, MAE, N e
   **Δ MAPE vs Pipeline Antiga** (antiga sempre na última linha como referência).
2. **Com vs sem feature**: pivô modelo × variante com o **Δ MAPE de cada variante contra a `base`**
   — mostra direto se `+mix`/`+seg`/`+seg_pca`/`bottom-up` ajudaram ou pioraram.
3. **Safra mensal**: heatmaps `mês × (modelo×variante)` de **MAPE** e de **viés** (centrado em 0),
   mais uma tabela longa `mês × modelo × {MAPE, viés, MAE}`.
4. **Gráficos**: barras de MAPE por variante (com a linha da antiga) e série temporal
   realizado × preditos das melhores combinações.
5. **Export**: `comparativo_canal_produto.xlsx` com as abas de ranking, com-vs-sem, safra, nulos e
   a `MASTER` completa.

> **Validação de nulos**: o notebook também reporta o **% do volume com canal/produto nulo** — é
> baixíssimo (canal ≈ 0,001%), então as features de segmento cobrem praticamente toda a base.
