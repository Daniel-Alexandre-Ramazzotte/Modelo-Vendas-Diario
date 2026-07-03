---
marp: true
theme: default
paginate: true
tags:
  - modelo
  - previsao
  - valor
  - quantidade
  - sarima
  - sarimax
  - intervencao
  - cointegracao
  - apresentacao
created: 2026-07-01
updated: 2026-07-02
author: Daniel Ramazzotte
disciplina: Econometria e Análise de Intervenção
style: |
  blockquote {
    border-left: 5px solid #1e3799; background: #eaf2ff;
    padding: 10px 16px; border-radius: 4px; margin: 12px 0; color: #0a3d62;
  }
  blockquote strong { color: #0a3d62; }
  section table { font-size: 16px; }
---

<!-- _class: cover -->
<!-- _paginate: false -->

# Modelagem SARIMA/SARIMAX das séries diárias de Valor **e** Quantidade de Propostas

## Econometria e Análise de Intervenção

Séries temporais clássicas, análise de intervenção (Box–Tiao) e teste de cointegração
aplicados **em pé de igualdade** às séries diárias de **valor (R$)** e **quantidade** de
propostas (etapa 16).

**Daniel Ramazzotte** · Julho/2026

---

## Agenda

**Parte I — Metodologia**
1. Construção da base
2. Teste de cointegração (método)
3. Análise de intervenção (método)
4. Método experimental — validação walk-forward
5. Métricas de comparação
6. Covariáveis
7. Modelos mensais (método)

**Parte II — Resultados** → Cointegração · Intervenção · Ranking · Modelos escolhidos e
adequação · Mensais

**Parte III —** Interpretação · Conclusão · Discussão

---

<!-- _class: section-divider -->

## Parte I — Metodologia

### Como as duas séries foram construídas, testadas e validadas

---

## 1. Construção da base

Agregação **diária** das propostas da etapa 16, apenas em **dias úteis** (exclui sábados,
domingos e feriados nacionais via `workadays`) → sazonalidade semanal regular **`m = 5`**.

| | **Valor (R$)** | **Quantidade** |
|---|---|---|
| Definição | valor monetário processado no dia | nº de propostas analisadas no dia |
| Fonte | `crefaz.ft_proposta` (etapa 16) | `crefaz.ft_proposta` (etapa 16) |
| Papel | série-alvo | série-alvo |

- **As duas séries têm o mesmo status:** cada uma recebe seleção de ordem, intervenção,
  ranking e modelo recomendado próprios.
- Histórico: **~410 dias úteis** (07/11/2024 → 01/07/2026).
- Janela de avaliação walk-forward: **N = 209** (valor) e **N = 211** (quantidade).

---

## As duas séries lado a lado

<div style="display:flex; gap:12px;">
<img src="img_sarima/valor_serie.png" style="width:50%;">
<img src="img_sarima/qtd_serie.png" style="width:50%;">
</div>

Séries com médias móveis de 5 e 20 dias; linhas verticais = dias de intervenção. Ambas
mostram **nível que passeia** (não-estacionário), **sazonalidade semanal** e **quedas
pontuais** nos dias de erro operacional.

---

## Análise clássica — estacionariedade e ACF/PACF

Antes de estimar: **estacionariedade** (ADF/KPSS), **autocorrelação** (ACF/PACF) e
**decomposição** (STL, período 5) — feitas para **as duas séries**.

![ACF/PACF do valor: nível decai lentamente (I(1)); 1ª diferença com corte no lag 1 (MA)](img_sarima/valor_acf.png)

- ACF em **nível decai lentamente** (valor e qtd) → não-estacionária → justifica `d = 1`.
- Na **1ª diferença**, pico negativo no lag 1 → assinatura de **MA(1)** em ambas.

---

## Decomposição STL (período = 5)

Tendência suave de médio prazo + **sazonalidade semanal clara** + resíduo com *spikes* nos
dias atípicos (que a intervenção trata). Padrão **idêntico** nas duas séries.

![Decomposição STL do valor: tendência, sazonal semanal e resíduo](img_sarima/valor_stl.png)

---

## 2. Teste de cointegração — o método

Cointegração testa-se nos **níveis**, não nas diferenças. O pré-requisito é que ambas as
séries sejam **I(1)** (não-estacionárias em nível, estacionárias na 1ª diferença).

- **Pergunta econômica:** se valor e quantidade forem cointegrados com vetor `(1, −β)`, o
  **ticket médio** (`valor / qtd`) seria estacionário → proporcionalidade estável no longo prazo.
- **Testes aplicados:** Engle–Granger e Johansen (traço) sobre os níveis; ADF do ticket médio;
  ADF com tendência (`ct`) para descartar *trend-stationarity*.

> **Por que importa:** decide se as duas séries devem ser modeladas **juntas** (VECM/ARDL)
> ou **separadamente**. É o teste que legitima tratar valor e quantidade como problemas
> independentes.

---

## 3. Análise de intervenção — o método (Box–Tiao)

Para cada **dia especial** (eventos do `Log_Erro` operacional + vésperas de feriado) ajustamos
o SARIMA/SARIMAX com **regressores de intervenção** e classificamos o efeito:

- **Pulso (impulso):** efeito **transitório**, restrito ao(s) dia(s) do evento
  (dummy = 1 no evento, 0 nos demais). Típico de **paradas operacionais**.
- **Degrau (step):** **mudança de nível permanente** a partir do evento
  (dummy = 0 antes, 1 do evento em diante). Típico de **mudanças estruturais**.

**Escolha por evento:** ajustam-se os dois modelos e fica-se com o de coeficiente
**significativo (p < 0,05)** e menor **AIC**. Aqui a série **mantém** os dias especiais —
é necessário para estimar o efeito.

> **Papel no ranking:** a intervenção **descontamina o ajuste** — os coeficientes AR/MA são
> estimados sem serem puxados pelos *spikes*. Nos dias avaliados (normais) as dummies valem 0.

---

## 4. Método experimental — walk-forward × ajuste normal

Replica a operação real: **retreina todo dia, prevê o próximo**. Aplicado igualmente às duas séries.

| | **Walk-forward** | **Normal (1 ajuste)** |
|---|---|---|
| Nº de ajustes | **N** (um por dia) | 1 |
| Usa dados futuros p/ estimar? | **Não** (sem vazamento) | in-sample: sim |
| O que mede | **Erro out-of-sample realista** | qualidade de ajuste |
| Onde no estudo | ranking e correção de viés | diagnóstico |

- **Dias atípicos** (`Log_Erro` + vésperas) saem do `datas_eval`: o ranking pontua só **dias normais**.
- **Correção de viés** (`aplica_debias`): corrige a próxima previsão pela média dos erros
  passados (janela 10 dias, `rolling + shift(1)` → sem vazamento).
- Comparação **maçã-com-maçã** com a **Pipeline Antiga** (backup), também previsão diária de 1 passo.

---

## 5. Métricas de comparação

O ranking é ordenado por **RMSPE** (penaliza erros grandes); as demais métricas dão o retrato completo.

| Métrica | O que mede |
|---|---|
| **MAPE médio %** | erro percentual absoluto médio (dia típico) |
| **RMSPE %** | raiz do erro quadrático percentual — **chave do ranking** (pune outliers) |
| **R²** | fração da variância explicada |
| **Viés (MPE)** | erro médio com sinal → super/subestimação sistemática |
| **Mediana %** | robusta a caudas |
| **% < 5% / < 10%** | acurácia operacional (dias dentro da meta) |

> **Meta de qualidade:** MAPE ≤ 5% (ideal) · ≤ 10% (aceitável), idêntica para valor e quantidade.

---

## 6. Covariáveis

A exógena é sempre de **D-1** (conhecida no momento da previsão → **sem vazamento**).

| Papel | **Valor** | **Quantidade** |
|---|---|---|
| Endógena `y_t` | valor diário (R$) | quantidade diária |
| **Exógena D-1** | `fila_d1` — fila de pagamento de ontem (etapa 15) | `valor_d1` — valor de ontem |
| Dummies calendário | dia-da-semana (`ter…sex`; 2ª = ref.) | idem |
| Intervenção | pulso/degrau dos dias especiais | idem |

- **Dummies de dia-da-semana** capturam o padrão semanal pelo **dia real**, robusto à ausência
  de feriados na grade (que desalinharia o lag `t-5`).
- **SARIMA puro permanece univariado** por design → o ranking mostra **diretamente se a exógena
  ajuda** (SARIMA sem × SARIMAX com). *Spoiler:* ajuda no valor, não na quantidade.

---

## 7. Modelos mensais — o método

Além do diário, avaliamos o **total do mês** de cada série por dois caminhos:

- **Nowcast:** realizado acumulado no mês + previsão SARIMAX dos dias úteis restantes →
  atualiza a estimativa do total dia a dia.
- **Modelo mensal supervisionado:** tabela com lags mensais + calendário (`n_uteis`, `mm3`,
  sazonais), janela expansível sem vazamento, comparando Naive, Média-Útil MM3, Ridge,
  RandomForest, Linear, Sazonal e SARIMA agregado.

> **Objetivo:** verificar se o esforço diário se traduz em bom total mensal, e qual é a
> referência mais simples que ninguém deveria perder.

---

<!-- _class: section-divider -->

## Parte II — Resultados

### Cointegração · Intervenção · Ranking · Modelos escolhidos · Mensais

---

## Resultado — Cointegração (não há cointegração confiável)

| Teste | Valor | Quantidade | Leitura |
|---|---|---|---|
| ADF nível | p = 0,848 | p = 0,529 | ambas **I(1)** |
| ADF 1ª diferença | p = 0,000 | p = 0,000 | estacionárias diferenciadas |
| **Engle–Granger** (conjunto) | \-\- | p = **0,962** | **NÃO rejeita** → sem cointegração |
| ADF do ticket médio | \-\- | p = 0,841 | erro de equilíbrio **não-estacionário** |

Relação de longo prazo estimada: `valor = −1.568.875 + 2.229,4 · qtd` (β ≈ ticket médio).
Johansen dá 1 relação (sem tendência) e 2 (com tendência), mas o ADF-`ct` (valor p=0,0007;
qtd p=0,0002) indica **trend-stationarity** — não cointegração genuína.

> **Conclusão:** o erro de equilíbrio **deriva** (não volta à média) → **modelar as séries
> separadamente**. Como as ordens ficam mistas I(0)/I(1), o *follow-up* correto é o **teste de
> limites ARDL** (Pesaran–Shin–Smith), não VECM.

![Níveis padronizados e resíduo de equilíbrio com deriva persistente](img_sarima/coint.png)

---

## Resultado — Intervenção: efeito por evento

**18 eventos** classificados em cada série (pulso × degrau). Predominam efeitos **negativos**
(paradas/erros derrubam a série); **Carnaval** aparece como **positivo** (acúmulo pós-feriado).

| Evento (exemplos) | Efeito no **Valor** | Efeito na **Quantidade** |
|---|---|---|
| Véspera Natal/Ano-Novo/Carnaval | −R$ 2,00 mi (abrupto) | −922 (abrupto) |
| Microsoft (29/10/2025) | −R$ 2,82 mi (abrupto) | −1.413 (abrupto) |
| CrefazOn-Cobrança (03/07/2025) | −R$ 1,28 mi (abrupto) | −705 (abrupto) |
| Carnaval (05/03/2025) | +R$ 1,77 mi (gradual) | +763 (abrupto) |

Classificação: **Valor** → 8 gradual, 5 abrupto, 5 n.s. (13 regressores) · **Quantidade** →
7 abrupto, 7 gradual, 4 n.s. (14 regressores).

![Efeito estimado por evento (abrupto × gradual) — série de valor / SARIMAX](img_sarima/interv_efeito.png)

---

## Resultado — a intervenção limpa o ajuste (pré × pós)

Comparando o SARIMA **sem** e **com** as dummies de intervenção (N = 410):

| Série | | AIC | DP resíduo | MAE resíduo | Ljung-Box p(10) |
|---|---|:---:|:---:|:---:|:---:|
| **Valor** | pré | 11.831,6 | R$ 620,0 k | R$ 434,2 k | **0,02** ❌ |
| | **pós** | **11.745,9** | **R$ 550,5 k** | **R$ 395,3 k** | **0,40** ✅ |
| **Quantidade** | pré | 5.742,2 | 359,1 | 246,4 | **0,01** ❌ |
| | **pós** | **5.654,3** | **326,9** | **230,7** | **0,38** ✅ |

- **AIC e desvio do resíduo caem** nas duas séries.
- **Ljung-Box deixa de rejeitar** (p sobe de ~0,01 para ~0,4): a autocorrelação residual que os
  *spikes* causavam **desaparece** → dinâmica de curto prazo bem capturada.

---

## Resultado — Estimação (coeficientes verificados)

Ajuste in-sample no histórico completo (N = 410), exógena padronizada (z-score):

| Coeficiente | **Valor** `SARIMAX(0,1,1)(0,0,1,5)` | **Quantidade** `SARIMAX(0,1,1)(0,0,2,5)` |
|---|---|---|
| **Exógena D-1** | `fila_d1` **+96,8 mil / dp** · p < 0,001 ✅ | `valor_d1` **−14,4** · p = 0,61 ❌ |
| `ma.L1` (choque de ontem) | −0,784 · p < 0,001 | −0,794 · p < 0,001 |
| `ma.S.L5` (semanal) | −0,111 · p = 0,019 | −0,128 · p = 0,009 |
| `ma.S.L10` | — | −0,087 · p = 0,131 |
| AIC (com exógena) | 11.827,5 | 5.744,6 |

> **O achado central, com significância estatística:** a **fila do dia anterior** é *driver*
> **forte e positivo** do valor (p < 0,001), mas o **valor de ontem NÃO ajuda** a prever a
> quantidade (p = 0,61). É exatamente por isso que o vencedor de cada série é diferente.

---

## Resultado — Ranking Valor (N = 209, por RMSPE)

| Modelo | MAPE % | RMSPE % | R² | Viés (R$) | Mediana % |
|---|:---:|:---:|:---:|:---:|:---:|
| **SARIMAX** | 7,32 | **9,21** | **0,753** | +9.651 | 6,02 |
| SARIMA (univariado) | 7,56 | 9,55 | 0,748 | −27.479 | 6,42 |
| Pipeline Antiga em Produção | **7,23** | 9,57 | 0,745 | +28.438 | 5,35 |
| SARIMAX (corrigido) | 7,57 | 9,71 | 0,733 | +5.655 | 6,14 |
| SARIMA (corrigido) | 7,86 | 10,02 | 0,722 | +3.958 | 6,51 |
| Log-retorno | 8,27 | 10,97 | 0,610 | +113.506 | 6,72 |

- **SARIMAX tem o melhor RMSPE e o melhor R²** de todos os candidatos.
- Fica ~0,1 p.p. atrás da Antiga só no **MAPE médio** — mas a Antiga é **retreinada quase
  diariamente**; o SARIMAX usa **uma única especificação**. A exógena `fila_d1` **agregou**.

---

## Resultado — Ranking Quantidade (N = 211, por RMSPE)

| Modelo | MAPE % | RMSPE % | R² | Viés | Mediana % |
|---|:---:|:---:|:---:|:---:|:---:|
| **SARIMA (univariado)** | **7,20** | **9,08** | **0,414** | +15,6 | 6,44 |
| SARIMA (corrigido) | 7,62 | 9,69 | 0,351 | +5,2 | 6,05 |
| SARIMAX | 7,31 | 9,79 | 0,319 | +1,0 | 5,52 |
| Pipeline Antiga em Produção | 7,89 | 9,88 | 0,313 | +40,5 | 6,42 |
| SARIMAX (corrigido) | 7,88 | 10,52 | 0,228 | +4,4 | 6,35 |
| Log-retorno | 8,10 | 10,86 | 0,089 | +97,8 | 6,90 |

> **Contraste decisivo:** para a **quantidade**, o **SARIMA univariado vence** — a exógena
> `valor_d1` **piora** o RMSPE. O padrão semanal `m = 5` já basta. Confirma o valor de deixar
> SARIMA e SARIMAX lado a lado no ranking.

---

## Resultado — Modelos escolhidos × Pipeline (capacidade preditiva)

Da função `comparar_modelo` (histórico completo), o modelo recomendado de cada série **bate a
Pipeline Antiga** onde importa:

| | Vencedor | Antiga | | Vencedor | Antiga |
|---|:---:|:---:|---|:---:|:---:|
| | **Valor — SARIMAX** | | | **Qtd — SARIMA** | |
| RMSPE % | **9,21** | 9,57 | | **9,08** | 9,88 |
| R² | **0,753** | 0,745 | | **0,414** | 0,313 |
| Dias < 10% | 153/209 | 154/209 | | **163/211** | 152/211 |
| Erro máx. % | **30,6** | 39,5 | | **30,5** | 34,1 |

**Recorte recente (janeiro em diante):** a vantagem **cresce** — Valor SARIMAX 8,66% vs Antiga
10,22% de RMSPE; Qtd SARIMA 8,67% vs 9,35%. Os modelos brancos são **mais estáveis** no período recente.

---

## Adequação e predição — diagnóstico dos resíduos

![plot_diagnostics do SARIMAX-Valor: resíduo padronizado, histograma vs N(0,1), Q-Q e correlograma](img_sarima/valor_diagnostico.png)

- **Autocorrelação:** correlograma dentro das bandas; Ljung-Box **não rejeita** → curto prazo
  bem modelado (**vale para as duas séries**).
- **Ressalvas (idem qtd):** **heterocedasticidade** e **caudas pesadas/assimetria** (Jarque-Bera
  significativo) — erros maiores nos dias atípicos. Justifica a intervenção + correção de viés.

---

## Valor — previsto × realizado (SARIMAX)

![SARIMAX × Realizado × Pipeline Antiga ao longo de todo o período de avaliação](img_sarima/valor_pred_real.png)

O SARIMAX acompanha bem nível e sazonalidade; os maiores erros concentram-se nos *saltos*
pós-atípicos (onde a Antiga também erra). A curva da quantidade (SARIMA) tem comportamento
análogo.

---

## Resultado — Modelos mensais

Ranking do **total do mês** (10 meses avaliados, ordenado por RMSPE):

| | **Valor** | | **Quantidade** | |
|---|:---:|:---:|:---:|:---:|
| Modelo | MAPE % | RMSPE % | MAPE % | RMSPE % |
| **Naive (mês-1)** | **3,54** | **4,66** | **2,94** | **3,64** |
| Média-Útil MM3 | 6,17 | 6,93 | 3,28 | 4,06 |
| Ridge | 8,50 | 10,28 | 6,39 | 8,17 |
| SARIMA (agregado) | 10,78 | 12,60 | 9,65 | 10,27 |

> **Achado:** para o **total mensal**, a **persistência simples (mês anterior)** domina — o
> SARIMA diário agregado **não** é competitivo nessa granularidade. O **nowcast** é a ferramenta
> certa de acompanhamento: converge para o realizado conforme o mês avança.

![Nowcast do total do mês (valor): converge para o realizado conforme o mês avança](img_sarima/nowcast_valor.png)

---

<!-- _class: section-divider -->

## Parte III — Interpretação, Conclusão e Discussão

---

## Interpretação

**O que os modelos revelam, com significância estatística:**

1. **Valor é *puxado* pela fila.** `fila_d1` é *driver* positivo e forte (+R$ 96,8 mil por
   desvio-padrão de fila, p < 0,001): a fila de pagamento de ontem antecipa o valor de hoje.
2. **Quantidade é *autossuficiente*.** O valor de ontem não informa a quantidade de hoje
   (p = 0,61); o que a governa é a **estrutura própria** (MA(1) + sazonalidade semanal).
3. **Dias de erro operacional têm efeito real e mensurável** (véspera −R$ 2,0 mi / −922
   propostas; Microsoft −R$ 2,8 mi / −1.413) → merecem **intervenção**, não descarte cego.
4. **Ambas as dinâmicas diárias** são bem descritas por **suavização MA(1)** (−0,78/−0,79) com
   leve componente semanal.
5. **Valor e quantidade NÃO compartilham equilíbrio de longo prazo** → modelagem separada é a
   escolha correta (ticket médio não-estacionário).

---

## Conclusão

> **Valor → SARIMAX `(0,1,1)(0,0,1,5)` + `fila_d1` + intervenção.**
> Melhor **RMSPE (9,21%)** e **R² (0,753)** do estudo; MAPE praticamente empatado com a
> Pipeline Antiga, com a vantagem decisiva de ser **interpretável**.

> **Quantidade → SARIMA univariado `(0,1,1)(0,0,2,5)` + intervenção.**
> A exógena não ajuda; o modelo univariado com sazonalidade semanal é o **melhor e o mais
> parcimonioso** (MAPE 7,20%, RMSPE 9,08%, R² 0,414) — e supera a Antiga em todas as métricas.

- Modelos **brancos** competitivos com o melhor ML e **superiores no RMSPE** nas duas séries.
- A **análise de intervenção** melhora o ajuste (AIC↓, Ljung-Box deixa de rejeitar) em ambas.
- **Sem cointegração** valor × qtd → séries modeladas separadamente.

---

## Discussão — limitações e próximos passos

**Limitações**
- **Heterocedasticidade e caudas pesadas** nos resíduos das duas séries (mitigadas por
  intervenção + debias, mas presentes) → intervalos de confiança otimistas nos extremos.
- **Classificação da forma** da intervenção (abrupto × gradual) tem pequeno *look-ahead*
  estrutural: é feita uma vez na série inteira (a maior parte é **calendário**, conhecido de
  antemão); os **coeficientes**, porém, são reestimados a cada dia no walk-forward.
- Modelos **mensais** mostram que, no total do mês, persistência simples vence — o SARIMA diário
  **não** é a ferramenta certa para essa granularidade.

**Próximos passos**
- **ARDL bounds test** como *follow-up* formal da cointegração (ordens mistas I(0)/I(1)).
- Injetar intervenções (Carnaval/vésperas) como **exógena futura determinística** no nowcast.
- Avaliar **reclassificação da intervenção dentro do walk-forward** (rigor total).

---

## Referências

- Notebook do experimento: [[experimento_sarimax]]
- Justificativa detalhada: `docs/justificativa_sarimax_valor.md`
- Scripts de produção: `scripts/producao/projecoes_valor.py`, `projecoes_qtd.py`
- Backups de previsão: `resultados/backup_valor.xlsx`, `backup_qtd.xlsx`
