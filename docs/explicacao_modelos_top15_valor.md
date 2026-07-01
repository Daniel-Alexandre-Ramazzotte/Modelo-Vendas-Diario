# Modelos que Superam a Pipeline em Produção — Valor

Análise do `top15_valor_realinhado.ipynb`. Na base consistente (N=266 dias comuns, dias com erro operacional removidos via `Log_Erro`), a **Pipeline em Produção tem MAPE médio de 9,15%** (mediana 6,89%). Dos candidatos avaliados, **5 a superam em MAPE médio**:

| # | Modelo | Tipo | MAPE médio | Mediana |
|---|--------|------|-----------|---------|
| 1 | `ExtraTrees(EXT,j90)` | Novo | **8,49%** | 6,45% |
| 2 | `Voting_log_ET(EXT,j90)` | Novo | 8,59% | **6,16%** |
| 3 | `BLEND_mean(EXT,j90)` | Novo | 8,65% | 6,22% |
| 4 | `GBR_logy(EXT,j90)` | Novo | 9,06% | 6,77% |
| 5 | `Voting(GBR+XGB+RFR)` | Sklearn | 9,14% | 7,05% |
| — | Pipeline em Produção | TPOT | 9,15% | 6,89% |

Diferente do modelo de quantidade (onde os vencedores eram pipelines TPOT resgatados da produção), aqui **os 4 primeiros são "candidatos novos"** desenhados no estudo de mediana — o sufixo `(EXT,j90)` indica as duas mudanças que eles compartilham. O 5º é um ensemble sklearn padrão. Na avaliação, todos são **retreinados do zero em cada fold**, nos mesmos folds alinhados ao backup. A coluna **Tipo** do ranking no notebook marca a origem de cada candidato: `Novo` (desenhados neste estudo), `TPOT` (pipelines resgatados da produção) e `Sklearn` (baselines padrão).

## O que significa `(EXT,j90)`

**`EXT` — features estendidas.** Os modelos padrão usam 9 features (`FEATS_BASE`): `dia_semana`, `lag_0` (quantidade de ontem), `lag_1` a `lag_6` (valor dos 6 dias anteriores) e `lag_7` (fila de ontem, etapa 15). Os candidatos novos acrescentam 8 (`FEATS_EXT`, 17 no total):

| Feature | O que captura |
|---------|---------------|
| `dia_mes`, `semana_mes`, `fim_mes` | Sazonalidade dentro do mês (`fim_mes` = flag para dia ≥ 25) |
| `ma3_valor`, `ma5_valor` | Médias móveis de 3 e 5 dias do valor — o "nível atual" da série, mais estável que um lag isolado |
| `ticket_1`, `ma3_ticket` | Ticket médio de ontem (valor/quantidade) e sua média móvel de 3 dias |
| `qnt_lag2` | Quantidade de anteontem |

**`j90` — janela de treino com as últimas 90 observações** anteriores ao dia previsto, o dobro da padrão (45). Cada observação é um dia com dado válido no treino — segunda a **sábado** (`INCLUIR_SABADO_TREINO=True`), excluindo domingos, feriados e dias com erro operacional — então 90 observações cobrem cerca de 3,5 meses de calendário. A janela maior estabiliza o erro nos dias típicos, o que aparece direto na mediana.

## #1 — `ExtraTrees(EXT,j90)` (MAPE 8,49% | mediana 6,45%)

`ExtraTreesRegressor` com 300 árvores extremamente aleatorizadas (os cortes de cada árvore são sorteados, não otimizados), sobre as 17 features estendidas. É o modelo mais simples do grupo — uma floresta única, sem transformação de alvo — e ainda assim o **melhor MAPE médio** do ranking inteiro. A aleatorização extra das árvores funciona como regularização natural, importante com janela de só 90 pontos.

## #2 — `Voting_log_ET(EXT,j90)` (MAPE 8,59% | mediana 6,16%)

Ensemble de votação que tira a média de **três** regressores:

1. **GradientBoosting com alvo em log** — `TransformedTargetRegressor(log1p/expm1)`: o modelo aprende a prever `log(1 + valor)` e a previsão é convertida de volta. Como valores monetários têm cauda longa (dias de pico muito acima do normal), trabalhar em log faz o modelo errar em termos **proporcionais** em vez de absolutos — exatamente o que o MAPE mede.
2. **XGBoost com alvo em log** — mesma ideia, outra implementação de boosting.
3. **ExtraTrees** (300 árvores, escala original) — o mesmo arquétipo do #1, dando o contraponto sem transformação.

Tem a **melhor mediana de todo o ranking (6,16%)**: nos dias típicos é o que erra menos.

## #3 — `BLEND_mean(EXT,j90)` (MAPE 8,65% | mediana 6,22%)

Não é um modelo treinado: é a **média aritmética das previsões dos 4 candidatos novos** (`ExtraTrees`, `GBR_logy`, `Voting_log_ET` e `GBR_ratio_ma5`). Vale notar que o quarto membro, `GBR_ratio_ma5` (prevê a razão valor/média móvel de 5 dias e multiplica de volta), **não bate a antiga sozinho** (9,37%), mas contribui com diversidade ao blend. O blend fica entre os membros na média, com mediana quase tão boa quanto o #2 — o perfil mais "seguro" do grupo.

## #4 — `GBR_logy(EXT,j90)` (MAPE 9,06% | mediana 6,77%)

`GradientBoostingRegressor` (300 árvores rasas, `max_depth=3`, `learning_rate=0.05`, `subsample=0.9`) com **alvo em log** — o membro 1 do voting do #2, sozinho. Boosting conservador: muitas árvores pequenas com passo curto e amostragem de 90% por árvore para reduzir variância. Vence a antiga nas duas métricas, mas mostra que o ganho maior do #2 vem da combinação, não deste membro isolado.

## #5 — `Voting(GBR+XGB+RFR)` (MAPE 9,14% | mediana 7,05%)

O único vencedor da configuração padrão (**features BASE, janela 45**): média das previsões de um GradientBoosting, um XGBoost e um RandomForest (200 árvores cada, `random_state=42`). Supera a antiga por margem mínima na média (9,14% vs 9,15%) e **perde na mediana** (7,05% vs 6,89%) — está aqui pelo critério de corte (MAPE médio), mas na prática empata com a produção.

## Leitura geral

- **O ganho vem da configuração, não do algoritmo**: o que separa os 4 primeiros do resto não é um modelo exótico, e sim **features estendidas + janela de 90 observações + alvo em log** — os mesmos algoritmos (ExtraTrees, GBR, XGB) com features BASE e janela 45 ficam atrás da antiga.
- **Média vs. mediana**: os 3 primeiros vencem a antiga com folga na mediana (6,16–6,45% vs 6,89%), indicando dia a dia mais previsível; a média segue puxada por dias atípicos.
- **Recomendação implícita do ranking**: `ExtraTrees(EXT,j90)` para minimizar o erro médio; `Voting_log_ET(EXT,j90)` (ou o blend) se o critério for o erro típico (mediana).
