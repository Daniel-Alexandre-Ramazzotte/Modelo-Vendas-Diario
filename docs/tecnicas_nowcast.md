# Técnicas de modelagem testadas — Nowcasting (Total e Estratos)

> Fonte: `notebooks/experimentos/experimento_mensal.ipynb`, seções "Nowcasting Total —
> Previsão do mês atual" (Seções 3–8) e "Nowcasting Estratos — Previsão do mês atual".
> Nowcast = previsão 1 passo à frente (mês corrente), walk-forward expansivo/rolling,
> sem vazamento (cada mês `t` só usa dados `< t`).

## Nowcasting Total (Seções 6–7: Valor e Quantidade)

Mesmo protocolo repetido para as duas áreas-alvo (`AREA VALOR - Total` e
`AREA QUANTIDADE - Total`).

### Baselines (Seção 5)
- **Naive (mês-1)** — repete o total do mês anterior.
- **MédiaUtil MM3** — média-útil dos 3 meses anteriores × dias úteis do mês-alvo.
- **SARIMAX (total, `n_uteis` exógeno)** — ajusta a série mensal do total, com dias úteis
  do mês como exógena determinística. Removido depois em favor da variante "média".

### Regressões e árvores (na MÉDIA por dia útil, reconstroem total × `n_uteis`)
- **Ridge** (`StandardScaler` + `Ridge(alpha=1.0)`)
- **RandomForest** (`n_estimators=300, max_depth=3, min_samples_leaf=2`) — testado no
  baseline, depois substituído pelas árvores abaixo
- **XGBoost**
- **AdaBoost**
- **LightGBM**
- **ExtraTrees**
- **GradientBoosting**
- **SARIMAX (média × dias úteis)** — auto-ARIMA na média por dia útil (sem exógena),
  reconstrói total multiplicando por `n_uteis[t]`
- **Naive Sazonal + Tendência** — repete a média do mesmo mês do ano anterior (t-12) +
  incremento YoY (t-1 vs t-13) como drift (variante de "seasonal naive + drift", Hyndman)

### Grid search de variáveis e janela
- Grid de **feature-set** (lags 1–3+mm3 até lags 1–24+mm3+mm6+mm12, e variante só com
  médias móveis) × **janela de treino** (rolling 6/12/24 meses) para Ridge + as 5 árvores
- TPOT testado neste grid e **descartado**: API nova trava indefinidamente (cluster Dask
  órfão), mesmo com `max_time_mins` baixo

### RIPR — Ridge com formas funcionais múltiplas
- Ridge (com Interações/Polinômios/Regressão): cada variável vira 6 formas funcionais
  (linear, quadrática, exponencial, arco-tangente, seno, cosseno sobre o z-score
  causal) + decil + spline cúbica natural (via `patsy`) — teste de limite (`p >> n`)
- **Grid search do RIPR**: modelo (**Ridge / Lasso / ElasticNet**) × `alpha`
  (0.1/1/10) × janela (6/12/24m) + poda das formas funcionais pouco significativas
  (abaixo da mediana de `|coeficiente|`)

### Blend / Stacking
- **Blend SARIMAX(média) + Naive** — peso fixo (grade 0.1–0.7)
- **Stacking (SARIMAX + Naive)** — meta-modelo (**Ridge / ExtraTrees / XGBoost**)
  aprendendo o peso via walk-forward
- **Blend final dos melhores candidatos** — média ponderada com pesos otimizados
  (`scipy.optimize`) **ou** stacking (Ridge/ExtraTrees/XGBoost), variando quantos
  candidatos entram (top 2/3/5); treino ≤ 2025, validação/escolha do vencedor em 2026
  (holdout genuíno), depois reaplicado no período comum (parte pré-2026 é in-sample)

### Kalman
- **Filtro de Kalman / modelo dinâmico linear** (`UnobservedComponents`,
  `level='local linear trend'`) — nível e inclinação como estados que mudam no tempo
  (passeio aleatório), ajustado na média por dia útil

### AutoML
- **TPOT** (busca evolutiva de pipeline) no feature-set estendido (lags 1–24 +
  MM3/6/12), janela rolling, search space `linear` (e `graph` opcional); timeout de
  90s com fallback para MédiaUtil MM3 (risco conhecido de travar via Dask)

### Correção de erros (pós-modelo, sobre o top 3)
- **Ridge sobre o resíduo** (walk-forward), usando 4 sinais defasados em 1 mês:
  `ticket_delta` (degrau de ticket médio), `changelog_score` (saldo de eventos de
  política), `share_trend` (inclinação do share da maior cia) e `entrada_saida_cia`
  (saldo líquido de cias entrando/saindo)

### Candidatos descartados (mencionados, não avançaram)
- Diário agregado (soma do previsto diário do ExtraTrees(BASE,j90)/ABR-2/SARIMA diário)
- Regressão Sazonal (OLS, Fourier + tendência global, h=1)
- Naive + Correção de Viés (testado nos estratos)

## Nowcasting Estratos (bottom-up)

Roda 1 walk-forward por estrato via `avaliar_mensal_estrato_completo` (drop-in de
`avaliar_mensal`, chamada por `_rodar_1_estrato`) e depois soma (bottom-up) para
comparar com o top-down. Desde a atualização mais recente, o roster de candidatos por
estrato é o **mesmo roster completo do Nowcasting Total (Seções 6/7), menos TPOT** —
antes só rodava o motor da Seção 5 (5 candidatos); agora inclui também árvores,
SARIMAX(média), Naive Sazonal, Grid Search, RIPR (simples + grid) e Blend/Stacking
SARIMAX+Naive:
- Naive (mês-1), MédiaUtil MM3, SARIMAX (total, `n_uteis` exógeno), Ridge, RandomForest
- SARIMAX (média × dias úteis), Naive Sazonal + Tendência
- XGBoost, AdaBoost, LightGBM, ExtraTrees, GradientBoosting
- Grid Search (feature-set × janela, vencedor) — controlado por `INCLUIR_GRID_SEARCH_ESTRATO`
- RIPR simples + RIPR grid (Ridge/Lasso/ElasticNet, vencedor e formas reduzidas) —
  controlado por `INCLUIR_RIPR_ESTRATO`; só produz candidato para estratos com
  histórico longo o bastante (~30+ meses, por causa dos lags até 24)
- Melhor Blend/Stacking SARIMAX(média)+Naive (peso fixo ou meta-modelo
  Ridge/ExtraTrees/XGBoost)
- Kalman (local linear trend)

**TPOT continua de fora**: mesmo problema de instabilidade (cluster Dask órfão) da
Seção 6/7, inviável em ~140 séries de estrato.

Cache reindexado sob o prefixo `avaliar_mensal_estrato_completo` (chave inclui
`_VERSAO_CANDIDATOS_ESTRATO`), incluindo o cache do Blend Bottom-up
(`testar_blends_estrato`) — o cache antigo (roster de 5 candidatos) foi apagado.

### Recortes (estratos) testados
1. **CIA/Produto** — CIA para produtos Elétrico + Produto para não-Elétrico (1 dimensão)
2. **Canal** — canal sozinho, todos os produtos
3. **CIA/Produto × Canal** — cruzamento das duas dimensões acima (só no Nowcasting
   Estratos, não entra na Trajetória Estratos por custo)
4. **CIA (unidade)** — mesma composição do recorte 1, mas cia individual em vez de
   cia-grupo (usado também na Comparação de Metas)

Estratos com histórico curto (abaixo do gate de cobertura) não são descartados: são
somados num grupo **"Outros"** e modelados juntos.

### Bottom-up simples
- Para cada estrato, escolhe o melhor modelo simples (menor RMSPE) entre TODOS os
  candidatos do roster completo acima e soma as previsões dos estratos
  (`agregar_estratos_mensal`)

### Bottom-up com Blend
- Para cada estrato, além do melhor modelo simples, testa **blends** entre os top-3
  modelos do próprio estrato: peso fixo (grade 0.3/0.5/0.7) e **stacking**
  (Ridge/ExtraTrees/XGBoost) para cada par — mesmas técnicas da Seção 6.8, aplicadas
  estrato a estrato; RMSPE decide se o blend supera o modelo simples

## Comparação final (Nowcasting Total × Nowcasting Estratos)

Compara o vencedor do Nowcasting Total (Seções 6/7) contra os três bottom-ups do
Nowcasting Estratos (CIA/Produto, Canal, CIA/Produto × Canal), lado a lado, no período
comum a todos os candidatos — sem escolher um único "vencedor" entre os recortes
bottom-up.
