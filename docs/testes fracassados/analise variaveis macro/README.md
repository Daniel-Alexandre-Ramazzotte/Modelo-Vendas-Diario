# Variáveis macro como exógenas no SARIMAX mensal — desemprego, salário mínimo, endividamento, Big Mac

**Pergunta:** os melhores modelos da trajetória mensal são SARIMAX e Naive(1) (estratificados). Variáveis
macro brasileiras (desemprego, salário mínimo, taxa de endividamento das famílias, índice Big Mac)
agregam sinal ao SARIMAX ou só adicionam ruído?

**Veredito: só adicionam ruído.** Nenhuma das 4 melhorou o SARIMAX baseline (total + `n_uteis` exógeno,
mesmo candidato do `experimento_mensal.ipynb`) em VALOR ou QTD; duas pioraram de forma estatisticamente
significativa. **Recomendação: não incluir.**

## Como rodar

```bash
python "analise variaveis macro/_exp_macro_exogenas.py"
```

Saída: prints no console + `saidas/macro_exogenas_teste.xlsx` (ranking + teste de Diebold-Mariano, uma
aba por target, aba `resumo` consolidada).

## Metodologia

1. Série mensal (2021-01 em diante, mesma decisão do `experimento_mensal.ipynb`) via a mesma query de
   propostas (etapa 16) e cache (`carregar_com_cache`, prefixo `query_mensal` — reaproveita o cache já
   populado pelo notebook).
2. Cada variável macro baixada e **defasada pela publicação real**, para não vazar informação do futuro:

   | Variável | Fonte | Defasagem aplicada | Motivo |
   |---|---|---|---|
   | `desemprego` | BCB SGS 24369 (Taxa de desocupação, PNAD Contínua/IBGE) | 2 meses | trimestre móvel, divulgado ~2 meses após o fechamento |
   | `salario_minimo` | BCB SGS 1619 | 0 | definido por decreto/lei, conhecido de antemão (mesmo racional do `n_uteis`) |
   | `comprometimento_renda` | BCB SGS 29034 (Comprometimento de renda das famílias com o serviço da dívida) | 3 meses | usado como **proxy** de "taxa de endividamento" — as séries diretas (SGS 19881/19882) foram **descontinuadas em 2021-08**, inúteis para o período avaliado aqui |
   | `bigmac_usd_raw` | The Economist, [big-mac-data](https://github.com/TheEconomist/big-mac-data) (`USD_raw`, Brasil) | 1 mês | semestral (jan/jul), preenchido para mensal via *forward-fill* |

3. Walk-forward expansivo, 1 passo, mínimo 6 meses de treino — **mesmo motor** do `wf_sarimax` do
   `experimento_mensal.ipynb` (`pm.auto_arima`, sazonal só com ≥24 meses de histórico).
4. Candidatos: baseline (`n_uteis`), cada macro isolada + `n_uteis`, e todas as 4 macro juntas + `n_uteis`
   (nunca testadas todas de uma vez sem o baseline isolado, para não confundir colinearidade com ganho real).
5. Comparação em duas camadas:
   - **Ranking bruto** (MAPE/RMSPE/Viés), cada candidato no período que conseguiu avaliar.
   - **Teste de Diebold-Mariano** (perda = erro²) contra o SARIMAX baseline, sempre no período **em comum**
     aos dois candidatos — decide estatisticamente se a diferença de erro é distinguível de ruído amostral
     (H0: mesma acurácia; p < 0,05 rejeita H0).
   - **Granger causality** (1ª diferença, defasagens 1–3) rodado à parte, só como triagem diagnóstica —
     não decide nada sozinho (N mensal pequeno = pouca potência estatística).

## Resultados

### VALOR

| Modelo | MAPE (%) | RMSPE (%) | Viés (real-prev) | N |
|---|---:|---:|---:|---:|
| **SARIMAX (baseline: n_uteis)** | 6.85 | **9.20** | 1.361.932,70 | 46 |
| Naive (mês-1) | 6.65 | 8.21 | 1.683.406,30 | 59 |
| SARIMAX + bigmac_usd_raw | 7.61 | 9.82 | 1.476.815,60 | 42 |
| SARIMAX + desemprego | 7.52 | 10.16 | 4.301.434,80 | 46 |
| SARIMAX + macro (todas) | 8.42 | 10.88 | 2.994.473,90 | 43 |
| SARIMAX + comprometimento_renda | 8.41 | 11.45 | 2.451.833,30 | 43 |
| SARIMAX + salario_minimo | 13.47 | 16.07 | 6.243.564,90 | 47 |

Diebold-Mariano vs. SARIMAX baseline:

| Modelo | DM stat | p-valor | N comum | Melhor que baseline? |
|---|---:|---:|---:|:---:|
| Naive (mês-1) | -1.041 | 0.3032 | 46 | não (indistinguível) |
| SARIMAX + desemprego | 0.086 | 0.9321 | 45 | não (indistinguível) |
| SARIMAX + bigmac_usd_raw | 0.486 | 0.6298 | 41 | não (indistinguível) |
| SARIMAX + macro (todas) | 0.463 | 0.6459 | 42 | não (indistinguível) |
| SARIMAX + comprometimento_renda | 2.373 | **0.0223** | 43 | **não — significativamente pior** |
| SARIMAX + salario_minimo | 4.340 | **0.0001** | 46 | **não — significativamente pior** |

### QTD

| Modelo | MAPE (%) | RMSPE (%) | Viés (real-prev) | N |
|---|---:|---:|---:|---:|
| **SARIMAX (baseline: n_uteis)** | 5.77 | **7.50** | 638,30 | 46 |
| Naive (mês-1) | 6.21 | 7.54 | 647,20 | 59 |
| SARIMAX + comprometimento_renda | 5.80 | 8.00 | 1.466,30 | 42 |
| SARIMAX + salario_minimo | 6.13 | 8.41 | 1.516,00 | 46 |
| SARIMAX + bigmac_usd_raw | 7.08 | 8.78 | 1.060,00 | 40 |
| SARIMAX + desemprego | 6.08 | 8.81 | 1.958,50 | 44 |
| SARIMAX + macro (todas) | 7.01 | 9.39 | 1.621,40 | 43 |

Diebold-Mariano vs. SARIMAX baseline: nenhuma diferença estatisticamente significativa (p entre 0.22 e
0.57 em todos os candidatos macro; Naive p=0.36) — mas o ranking bruto já mostra todo mundo pior que o
baseline, então "não significativo" aqui só confirma que não há nem sinal de ganho, positivo ou negativo.

### Granger causality (triagem, 1ª diferença)

`desemprego` foi a única variável com p-valor baixo (0.007–0.03 nos lags 2–3, em VALOR e QTD) —
sugerindo, isoladamente, alguma relação causal-no-sentido-de-Granger com a série. **Isso não se traduziu
em ganho real no walk-forward** (RMSPE piora tanto em VALOR quanto em QTD, DM test indistinguível de
ruído): padrão clássico de correlação que aparece em amostra mas não sobrevive fora dela, plausivelmente
por causa do N pequeno (~44–46 meses avaliados) fazendo o `auto_arima` overfitar a exógena extra.
`salario_minimo`, `comprometimento_renda` e `bigmac_usd_raw` não mostraram nenhum sinal de causalidade
mesmo no teste diagnóstico (p > 0.1 em todos os lags).

## Ressalvas

- Teste rodado na série **TOTAL**, não nos estratos (CIA/canal) onde os melhores resultados do
  `experimento_mensal.ipynb` foram observados ("estratos 1D"). Dado que o sinal já saiu limpo e negativo
  aqui, estender para estratos tem custo computacional alto (mais walk-forwards com `auto_arima`) para um
  resultado que provavelmente se repete — não fiz, mas é a extensão natural se algum dia quiser confirmar.
- `comprometimento_renda` (SGS 29034) é um **proxy**, não a série direta de "endividamento das famílias"
  pedida — a série direta (SGS 19881/19882) está descontinuada desde 2021-08.
- N mensal pequeno (~46–60 meses avaliados) limita a potência do teste — ausência de melhora
  estatisticamente significativa não é prova definitiva de efeito zero, mas combinada com o RMSPE
  piorando na maioria dos candidatos, é um sinal consistente de ruído, não de sinal perdido.
