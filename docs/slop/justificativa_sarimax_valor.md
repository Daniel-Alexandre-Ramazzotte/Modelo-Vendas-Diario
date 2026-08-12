# SARIMAX — Modelo de Valor: justificativa, coeficientes e interpretação

Seção de relatório sobre o modelo **SARIMAX** avaliado na Parte 5 do
`experimento_valor_vies.ipynb` (e detalhado no `experimento_sarimax.ipynb`). É o melhor
candidato **clássico de séries temporais** para a série diária de valor das propostas
(etapa 16) e o melhor candidato **novo** do estudo depois da correção de viés.

## 1. O que é o modelo e por que ele foi escolhido

SARIMAX = **S**easonal **A**uto**R**egressive **I**ntegrated **M**oving **A**verage with
e**X**ogenous regressors. É a generalização do ARIMA que acrescenta dois elementos
indispensáveis para esta série:

- **Sazonalidade semanal** (`s = 5` dias úteis): segunda a sexta têm patamares diferentes;
- **Regressores exógenos**: variáveis externas que ajudam a prever o valor do dia.

A justificativa para usá-lo, em vez de só ML/TPOT, é tripla:

1. **É um modelo branco, não caixa-preta.** Cada termo tem significado estatístico
   (média móvel, sazonalidade, efeito da fila, efeito dos dias de erro) e vem com
   coeficiente, erro-padrão e p-valor — ao contrário dos pipelines TPOT, cuja arquitetura
   empilhada não permite ler "o quanto a fila pesa".
2. **Modela explicitamente a estrutura temporal** (tendência via diferenciação, choque do
   dia anterior via MA, sazonalidade semanal), que os modelos de ML só capturam de forma
   indireta via lags como features.
3. **Trata os dias atípicos de forma transparente**, com uma dummy de intervenção
   (modelo de intervenção de Box–Tiao) para os dias de erro operacional, em vez de
   simplesmente removê-los.

E, no fim, **ele performa**: na avaliação walk-forward 1-passo (mesmos folds dos demais
candidatos, janela e datas idênticas), o SARIMAX foi o **melhor entre os modelos de série
temporal** e o **melhor entre todos os 82 candidatos novos** após a correção de viés —
ficando atrás apenas da Pipeline Antiga em Produção (que é retreinada quase diariamente).

| Modelo | Parte | MAPE médio | RMSPE | R² | N |
|--------|-------|-----------:|------:|---:|--:|
| **SARIMAX** | P5 | **8,28%** | **10,29%** | **0,69** | 207 |
| LogRet+interv | P5 | 8,65% | 10,51% | 0,69 | 207 |
| SARIMA (univariado) | P5 | 8,79% | 10,64% | 0,68 | 207 |
| POLY+ABR (melhor TPOT) | P4 | 8,67% | 11,01% | 0,67 | 207 |
| Pipeline Antiga em Produção | REF | 7,22% | 9,57% | 0,75 | 209 |

> Valores da base integrada comum (N=207, dias atípicos de `Log_Erro` removidos, **com**
> correção de viés). Sem a correção, o SARIMAX marca MAPE 8,08% / RMSPE 9,95%. A correção
> quase zera o viés (de +R$52,2 mil para +R$1,3 mil) ao custo de ~0,34 p.p. de RMSPE.

## 2. Como o modelo foi estimado

Especificação (a mesma em todos os folds):

- **Ordem** `SARIMA(0,1,1)(0,0,1,5)`, selecionada **uma vez** por `pmdarima.auto_arima`
  (busca stepwise por AIC, sazonalidade `m=5`), com *fallback* fixo `(1,1,1)(1,0,1,5)`.
  - `(0,1,1)` na parte não-sazonal: **1 diferença** (`d=1`) remove a tendência/nível
    (a série é I(1) — não-estacionária em nível, estacionária na 1ª diferença, confirmado
    por ADF/KPSS) + **MA(1)** capta o choque do dia anterior;
  - `(0,0,1,5)`: **MA(1) sazonal** no lag 5 capta o padrão semanal.
- **Exógena** `fila_d1` (`lag_7`): a **fila de pagamento do dia anterior** (etapa 15),
  D-1. É a variável que antecipa o volume que será processado no dia seguinte.
- **Intervenção** `pulso_erro`: dummy de **pulso** (=1 nos dias de `Log_Erro`, 0 nos
  demais) que absorve, dentro do treino, a queda dos dias de erro operacional — para que
  esses outliers não contaminem a estimativa dos demais coeficientes.

**Avaliação walk-forward 1-passo** (`TimeSeriesSplit(test_size=1)`, janela
`max_train_size = JANELA_DIAS`): a cada fold o modelo é **reajustado** com o histórico
disponível e prevê **um único dia** à frente, usando o `fila_d1` e o `pulso_erro` daquele
dia. Isso reproduz exatamente a operação real (prever o próximo dia útil) e permite
comparar de igual para igual com os modelos de ML/TPOT (mesmas datas, mesma janela).
Em seguida aplica-se a **mesma correção de viés** walk-forward (janela 10 dias, sem
vazamento) usada em todos os candidatos.

## 3. Coeficientes (ajuste in-sample no histórico completo)

Como cada fold reajusta o modelo, não há um único vetor de coeficientes "de produção".
Para **leitura e interpretação**, ajusta-se o SARIMAX uma vez sobre **todo o histórico**
(N=404 dias úteis, 08/11/2024 → 23/06/2026), com a fila D-1 **padronizada (z-score)** e a
dummy de pulso:

```
                    SARIMAX(0,1,1)x(0,0,1,5)  —  N=404  —  AIC=11631
================================================================================
                 coef        std err      z       P>|z|     interpretação
--------------------------------------------------------------------------------
fila_d1_z     +1,027e+05    2,34e+04    +4,38    0,000   efeito da fila D-1 (padronizada)
pulso_erro    -4,545e+05    9,30e+04    -4,89    0,000   efeito dos dias de erro
ma.L1            -0,7829      0,034    -22,87    0,000   choque (MA não-sazonal)
ma.S.L5          -0,0862      0,046     -1,87    0,062   sazonal semanal (limítrofe)
sigma2          3,264e+11      —          —      0,000   variância do resíduo
================================================================================
```

> Comparação de AIC: SARIMA univariado (sem exógena/intervenção) = 11.640; SARIMAX com
> `fila_d1` + `pulso_erro` = **11.631**. Os dois regressores reduzem o AIC e ambos são
> altamente significativos (p < 0,001).

### Interpretação de cada termo

- **`fila_d1` (+R$102,7 mil por desvio-padrão, p < 0,001).** Quanto maior a fila de
  pagamento ontem, maior o valor processado hoje — relação **positiva e forte**. O
  coeficiente está na escala padronizada: cada **+1 desvio-padrão de fila (~54 propostas)
  acrescenta ~R$102,7 mil** ao valor previsto do dia; em escala bruta, **~R$1,9 mil por
  proposta** a mais na fila do dia anterior. É a confirmação quantitativa de que a fila é
  um bom *driver* antecedente do valor.

- **`pulso_erro` (−R$454,5 mil, p < 0,001).** Nos dias de erro operacional o valor
  processado cai, em média, **~R$454,5 mil** — cerca de **−10% sobre a média diária**
  (~R$4,6 milhões). O coeficiente negativo e significativo **valida tratar esses dias como
  intervenção**: são quedas reais e mensuráveis, não ruído, e isolá-las protege a
  estimativa dos demais parâmetros.

- **`ma.L1` (−0,783, p < 0,001).** Termo de média móvel de ordem 1, sobre a série
  diferenciada (`d=1`). Em um IMA(1,1), isto equivale a uma **suavização tipo média móvel
  exponencial**: a previsão do próximo dia é, essencialmente, o nível atual **corrigido por
  78% do choque (erro de previsão) de ontem**. Coeficiente grande e muito significativo —
  é o principal mecanismo preditivo do modelo.

- **`ma.S.L5` (−0,086, p = 0,062).** Componente **sazonal semanal** (lag 5 dias úteis).
  Negativo, porém **limítrofe** (p ≈ 0,06): há um resíduo de padrão semanal, mas fraco —
  a maior parte da sazonalidade já é absorvida pela diferenciação e pelo dia-da-semana
  implícito na janela útil.

- **`sigma2`.** Variância do termo de erro. O valor elevado reflete a escala monetária da
  série (milhões de reais), não um problema de ajuste.

### Diagnóstico e ressalvas

- **Resíduos:** Ljung-Box no lag 1 não rejeita ausência de autocorrelação (Prob(Q) ≈ 0,67)
  — o modelo capturou bem a dinâmica de curto prazo. Há, porém, **heterocedasticidade**
  (Prob(H) ≈ 0,00) e **caudas pesadas / assimetria** (Jarque-Bera significativo,
  curtose ≈ 8,5): os erros são maiores em dias atípicos, o que justifica a correção de
  viés aplicada por cima e a intervenção dos dias de erro.
- **Matriz de covariância quase singular** (`sigma2` muito grande): os **erros-padrão dos
  coeficientes podem ser instáveis**. A significância de `fila_d1` e `pulso_erro` é robusta
  (z ≈ 4–5), mas o número exato de `sigma2`/intervalos deve ser lido com cautela.

## 4. Conclusão para o relatório

O SARIMAX entrega desempenho **competitivo com o melhor TPOT** (e superior a ele após a
correção de viés) com a vantagem decisiva de ser **interpretável**: mostra, com
significância estatística, que (i) a **fila do dia anterior** é um *driver* positivo e forte
do valor, (ii) os **dias de erro operacional** derrubam o valor em ~10% e merecem
tratamento explícito, e (iii) a dinâmica diária é bem descrita por uma suavização do tipo
média móvel com leve componente semanal. Não substitui a Pipeline Antiga em Produção
(retreinada quase diariamente, RMSPE 9,57%), mas é o **melhor candidato novo do estudo** e
serve tanto de *benchmark* clássico quanto de ferramenta diagnóstica do que move a série.
